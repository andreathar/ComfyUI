"""Disposable SQLite evaluation, not imported by Brain or production Studio."""
import collections
import hashlib
import json
from pathlib import Path
import resource
import sqlite3
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / 'user/workflow_monitor/runs'
STREAM = '--stream' in sys.argv
TAG = '-profile' if '--profile' in sys.argv else '-stream' if STREAM else ''
DB = OUT / ('evaluation' + TAG + '.sqlite')
sys.path.insert(0, str(ROOT / '.codex/worktrees/workflow-monitor-brain'))
from workflow_monitor.benchmark import benchmark_report
from workflow_monitor.model import digest


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)


def load_sources(manifest):
    for directory in sorted(SOURCE.iterdir()):
        if not (directory / 'run.json').is_file():
            continue
        loaded = {}
        for name in ('run.json', 'events.jsonl', 'samples.jsonl'):
            path = directory / name
            if path.is_symlink():
                raise ValueError('Symlink source is outside this spike scope')
            raw = path.read_bytes() if path.exists() else None
            manifest[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest() if raw is not None else None
            loaded[name] = (json.loads(raw) if name == 'run.json' else [json.loads(line) for line in raw.splitlines()]) if raw is not None else []
        run = loaded['run.json']
        if run['status'] in ('queued', 'running'):
            raise ValueError('This evaluation requires a completed-run snapshot')
        report = benchmark_report(run, loaded['events.jsonl'][-10000:], len(loaded['events.jsonl']) > 10000)
        yield run, loaded['events.jsonl'], loaded['samples.jsonl'], report


def quality(run, events, samples, report):
    issues = []
    def gap(code, field, detail):
        issues.append((code, field, detail))
    provenance = run.get('provenance') or {}
    if provenance.get('status') != 'collected':
        gap('source_provenance_missing', 'provenance.status', provenance.get('status', 'absent'))
    else:
        snapshot = provenance['snapshot']
        if digest(snapshot) != provenance.get('snapshot_sha256'):
            gap('source_digest_mismatch', 'provenance.snapshot_sha256', 'snapshot does not match its digest')
        if snapshot.get('source_coverage') != 'complete':
            gap('source_coverage_partial', 'provenance.snapshot.source_coverage', str(snapshot.get('source_coverage')))
        for component in snapshot.get('components', []):
            if component.get('dirty') is not False:
                gap('dirty_or_unknown_source', 'provenance.snapshot.components', component['root'])
    if report['coverage']['events'] != 'complete':
        gap('event_coverage', 'coverage.events', report['coverage']['events'])
    if not samples:
        gap('resource_samples_missing', 'samples.jsonl', 'no samples stored')
    if run.get('sample_count', 0) != len(samples):
        gap('sample_count_mismatch', 'sample_count', f"metadata={run.get('sample_count')} stored={len(samples)}")
    if report['unresolved_inputs']:
        gap('unresolved_inputs', 'captured.unresolved', str(len(report['unresolved_inputs'])))
    for key in ('runtime_settings', 'input_package', 'prompt_review'):
        if report['coverage'][key] == 'unavailable':
            gap(key + '_missing', 'coverage.' + key, 'no validated native output attestation')
    if report['coverage']['artifact_identity'] != 'verified':
        gap('model_identity_unverified', 'coverage.artifact_identity', 'filename or residency is not a weight hash')
    if not report['output_evidence']:
        gap('output_identity_missing', 'output_evidence', 'no verified output hash')
    elif any(o.get('decode') != 'verified' for o in report['output_evidence']):
        gap('output_decode_unverified', 'output_evidence.decode', 'hashing is not decoding')
    if not report['visual_reviews']:
        gap('visual_review_missing', 'visual_reviews', 'no submitted findings')
    if report['event_window_truncated']:
        gap('report_event_window_truncated', 'events.jsonl', 'report uses last 10000 events; raw stream retained')
    gap('thermal_causality_unavailable', 'samples.devices', 'clock, power and throttle-reason fields not collected')
    return issues


def create_snapshot(records, manifest):
    if DB.exists():
        raise FileExistsError('Use a fresh output path; evaluation is not an incremental writer')
    connection = sqlite3.connect(DB)
    connection.executescript('''
      PRAGMA foreign_keys=ON;
      CREATE TABLE runs(run_id TEXT PRIMARY KEY, label TEXT, status TEXT, created REAL,
        wall_s REAL, events_coverage TEXT, provenance_status TEXT, sample_count INTEGER,
        report_json TEXT NOT NULL, raw_json TEXT NOT NULL);
      CREATE TABLE source_files(path TEXT PRIMARY KEY, sha256 TEXT);
      CREATE TABLE events(run_id TEXT REFERENCES runs, ordinal INTEGER, kind TEXT,
        payload_json TEXT NOT NULL, PRIMARY KEY(run_id,ordinal));
      CREATE TABLE samples(run_id TEXT REFERENCES runs, ordinal INTEGER, received REAL,
        process_rss_bytes REAL, payload_json TEXT NOT NULL, PRIMARY KEY(run_id,ordinal));
      CREATE TABLE device_samples(run_id TEXT, ordinal INTEGER, device TEXT,
        temperature_c REAL, memory_bytes REAL, utilization_percent REAL,
        FOREIGN KEY(run_id,ordinal) REFERENCES samples(run_id,ordinal));
      CREATE TABLE components(run_id TEXT REFERENCES runs, root TEXT, revision TEXT,
        dirty INTEGER, PRIMARY KEY(run_id,root));
      CREATE TABLE issues(run_id TEXT REFERENCES runs, code TEXT, field TEXT, detail TEXT);
      CREATE INDEX issues_by_code ON issues(code,run_id);
      CREATE INDEX device_by_temperature ON device_samples(temperature_c,run_id);
      CREATE VIEW model_report_runs AS SELECT run_id,label,status,wall_s,events_coverage,
        provenance_status,sample_count FROM runs;
    ''')
    with connection:
        for run, events, samples, report in records:
            rid = run['prompt_id']
            p = run.get('provenance') or {}
            connection.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?)',
                (rid, run.get('label'), run['status'], run.get('created'), report['admitted_wall_seconds'],
                 report['coverage']['events'], p.get('status', 'absent'), len(samples), encoded(report), encoded(run)))
            connection.executemany('INSERT INTO events VALUES (?,?,?,?)',
                ((rid, i, e.get('type'), encoded(e)) for i, e in enumerate(events)))
            for i, sample in enumerate(samples):
                connection.execute('INSERT INTO samples VALUES (?,?,?,?,?)',
                    (rid, i, sample.get('received'), sample.get('proc_rss'), encoded(sample)))
                connection.executemany('INSERT INTO device_samples VALUES (?,?,?,?,?,?)',
                    ((rid, i, f"{d.get('type')}:{d.get('index')}", d.get('temperature'), d.get('nvml_used'), d.get('gpu_util'))
                     for d in sample.get('devices', [])))
            connection.executemany('INSERT INTO components VALUES (?,?,?,?)',
                ((rid, c['root'], c.get('commit'), c.get('dirty')) for c in p.get('snapshot', {}).get('components', [])))
            connection.executemany('INSERT INTO issues VALUES (?,?,?,?)',
                ((rid, *issue) for issue in quality(run, events, samples, report)))
        connection.executemany('INSERT INTO source_files VALUES (?,?)', manifest.items())
    assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not connection.execute('PRAGMA foreign_key_check').fetchall()
    connection.close()


def timing(fn, count=15):
    elapsed = []
    result = None
    for _ in range(count):
        started = time.perf_counter()
        result = fn()
        elapsed.append((time.perf_counter()-started)*1000)
    return {'median_ms': statistics.median(elapsed), 'max_ms': max(elapsed), 'repeats': count}, result


def main():
    rss = {}
    def sample_rss(stage):
        rows = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
        rss[stage] = {k: int(rows[k].split()[0])/1024 for k in ('VmRSS', 'VmHWM')}
    sample_rss('start')
    started = time.perf_counter()
    manifest = {}
    records = load_sources(manifest) if STREAM else list(load_sources(manifest))
    load_seconds = time.perf_counter()-started
    sample_rss('loaded')
    started = time.perf_counter()
    create_snapshot(records, manifest)
    import_seconds = time.perf_counter()-started
    sample_rss('imported')
    # Detect source edits across the import; never publish this as current if they changed.
    for path, expected in manifest.items():
        p = ROOT/path
        actual = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        assert actual == expected, path
    c = sqlite3.connect(DB.as_uri()+'?mode=ro', uri=True)
    c.execute('PRAGMA query_only=ON')
    probes = {}
    probes['state_counts'], sql = timing(lambda: c.execute('SELECT status,count(*) FROM runs GROUP BY status ORDER BY status').fetchall())
    file_timing, direct = timing(lambda: sorted(collections.Counter(json.loads(p.read_text())['status'] for p in SOURCE.glob('*/run.json')).items()))
    assert sql == direct
    probes['state_counts']['json_scan'] = file_timing
    probes['coverage_gaps'], gaps = timing(lambda: c.execute('SELECT code,count(DISTINCT run_id) FROM issues GROUP BY code ORDER BY code').fetchall())
    probes['temperature_peaks'], peaks = timing(lambda: c.execute('SELECT run_id,max(temperature_c) FROM device_samples GROUP BY run_id ORDER BY run_id').fetchall())
    expected = []
    for run, events, samples, report in load_sources({}):
        values = [d['temperature'] for s in samples for d in s.get('devices', []) if d.get('temperature') is not None]
        if any(s.get('devices') for s in samples):
            expected.append((run['prompt_id'], max(values) if values else None))
    assert peaks == sorted(expected)
    probes['source_revisions'], components = timing(lambda: c.execute('SELECT root,revision,count(*) FROM components GROUP BY root,revision ORDER BY root').fetchall())
    blocked = False
    try:
        c.execute("DELETE FROM runs")
    except sqlite3.OperationalError:
        blocked = True
    assert blocked
    # JSON extraction can coerce unsigned 64-bit seeds to REAL; JSON text must be decoded in Python instead.
    large_seed = 18446744073709551615
    seed_json = encoded({'seed': large_seed})
    extracted = c.execute("SELECT json_extract(?, '$.seed')", (seed_json,)).fetchone()[0]
    preserved = json.loads(c.execute('SELECT ?', (seed_json,)).fetchone()[0])['seed']
    assert preserved == large_seed
    counts = {table: c.execute('SELECT count(*) FROM '+table).fetchone()[0]
              for table in ('runs','events','samples','device_samples','components','issues')}
    packet = {'schema':'brain-advisor-evaluation.v1','purpose':'data only, not model instructions',
              'dataset_sha256':digest(manifest),'source':'Brain completed-run snapshot',
              'counts':counts,'quality_gap_run_counts':dict(gaps),
              'selected_runs':[], 'rules':['Cite run IDs and evidence fields for claims.',
                'Unknown is not zero; missing evidence is not a negative measurement.',
                'No model ranking or cooling-effect claim follows from unmatched observations.',
                'Propose a test with rationale and missing evidence; never apply changes.'],
              'local_model_invoked':False}
    for raw, reported in c.execute('SELECT raw_json,report_json FROM runs ORDER BY created DESC LIMIT 3'):
        run, report = json.loads(raw), json.loads(reported)
        packet['selected_runs'].append({'run_id':run['prompt_id'],'label':run.get('label'),
            'source_run_sha256':manifest[str((SOURCE/run['prompt_id']/'run.json').relative_to(ROOT))],
            'status':run['status'],'coverage':report['coverage'],'phase_seconds':report['phase_seconds'],
            'peaks':report['peaks'],'configured_models':report['configured_models'],
            'unresolved_input_count':len(report['unresolved_inputs']),
            'quality_issues':[{'code':code,'field':field,'detail':detail} for code,field,detail in
                c.execute('SELECT code,field,detail FROM issues WHERE run_id=?', (run['prompt_id'],))]})
    sample_rss('queried')
    packet_path = OUT / ('model-evidence-packet' + TAG + '.json')
    packet_path.write_text(encoded(packet)+'\n')
    result={'disposable':True,'stream_one_run_at_a_time':STREAM,'sqlite_version':sqlite3.sqlite_version,'source_load_seconds':load_seconds,
            'sqlite_import_seconds':import_seconds,'source_bytes':sum((ROOT/p).stat().st_size for p,h in manifest.items() if h),
            'database_bytes':DB.stat().st_size,'process_peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            'proc_memory_mib':rss,
            'counts':counts,'probes':probes,'quality_gap_run_counts':dict(gaps),'read_only_write_blocked':blocked,
            'large_seed_json_extract_type':type(extracted).__name__,'large_seed_text_roundtrip_exact':preserved==large_seed,
            'source_hashes_unchanged':True,'integrity_check':'ok','model_packet_bytes':packet_path.stat().st_size,
            'limitations':['Warm-cache local measurement, not production-load performance.',
              'Stream import time includes source reading and report construction; non-stream import excludes those.',
              'State-count JSON scan and SQL match; derived quality-query speed excludes derivation cost.',
              'No incremental sync, watcher, live write, production integration or model inference.']}
    (OUT/'source-hashes.json').write_text(encoded(manifest)+'\n')
    (OUT/('result' + TAG + '.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
