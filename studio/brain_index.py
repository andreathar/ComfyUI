"""Rebuildable, local-only analysis snapshots of authoritative Brain records."""
import collections
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import time
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / 'user/workflow_monitor/runs'
DEFAULT_ANALYSIS = ROOT / 'user/workflow_monitor/analysis'
BRAIN = ROOT / 'custom_nodes/ComfyUI-Workflow-Monitor-Brain/workflow_monitor'
FILES = ('run.json', 'events.jsonl', 'samples.jsonl')
TERMINAL = {'succeeded', 'failed', 'interrupted', 'unknown-after-restart'}
MAX_RUN_BYTES = 100 * 1024 * 1024
MAX_LINE_BYTES = 256 * 1024
SCHEMA = 'brain-analysis.v1'


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def safe_numbers(value):
    if isinstance(value, int) and abs(value) > 2**53 - 1:
        return str(value)
    if isinstance(value, dict):
        return {k: safe_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [safe_numbers(v) for v in value]
    return value


def invalid_constant(value):
    raise ValueError('Non-finite JSON number: ' + value)


def decode(value):
    return json.loads(value, parse_constant=invalid_constant)


def run_id(value):
    if str(UUID(value)) != value:
        raise ValueError('Expected canonical run UUID')
    return value


def analyzer_identity():
    paths = [BRAIN / name for name in ('__init__.py', 'benchmark.py', 'model.py', 'quality.py')]
    paths.append(Path(__file__))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def analyzer():
    identity = analyzer_identity()
    name = '_studio_brain_' + sha(identity)
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, BRAIN / '__init__.py', submodule_search_locations=[str(BRAIN)])
        package = importlib.util.module_from_spec(spec)
        sys.modules[name] = package
        spec.loader.exec_module(package)
    module = importlib.import_module(name + '.benchmark')
    if analyzer_identity() != identity:
        raise ValueError('Brain analyzer changed while loading')
    return module.benchmark_report, identity


def file_identity(path):
    if path.is_symlink():
        raise ValueError('Symlink source rejected')
    if not path.exists():
        return None
    before = path.stat()
    if not path.is_file() or before.st_size > MAX_RUN_BYTES:
        raise ValueError('Invalid source file or size')
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(chunk)
            if size > MAX_RUN_BYTES:
                raise ValueError('Source exceeds size limit')
            digest.update(chunk)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('Source changed during hashing')
    return {'sha256': digest.hexdigest(), 'bytes': size, 'mtime_ns': after.st_mtime_ns, 'inode': after.st_ino}


def identities(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Invalid run directory')
    result = {name: file_identity(folder / name) for name in FILES}
    if sum(v['bytes'] for v in result.values() if v) > MAX_RUN_BYTES:
        raise ValueError('Run exceeds size limit')
    return result


def json_lines(path):
    if not path.exists():
        return
    with path.open('rb') as stream:
        total = 0
        while line := stream.readline(MAX_LINE_BYTES + 1):
            total += len(line)
            if total > MAX_RUN_BYTES:
                raise ValueError('JSONL stream exceeds run limit')
            if len(line) > MAX_LINE_BYTES:
                raise ValueError('JSONL line exceeds limit')
            value = decode(line)
            if not isinstance(value, dict):
                raise ValueError('JSONL record must be an object')
            yield value


def number(value):
    return value if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) else None


SQL = '''
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(value TEXT NOT NULL);
CREATE TABLE runs(run_id TEXT PRIMARY KEY, status TEXT, label TEXT, created REAL,
 wall_s REAL, sample_count INTEGER, event_count INTEGER, report_json TEXT NOT NULL);
CREATE TABLE sources(run_id TEXT REFERENCES runs, name TEXT, identity_json TEXT NOT NULL, PRIMARY KEY(run_id,name));
CREATE TABLE events(run_id TEXT REFERENCES runs, ordinal INTEGER, kind TEXT, payload_json TEXT, PRIMARY KEY(run_id,ordinal));
CREATE TABLE samples(run_id TEXT REFERENCES runs, ordinal INTEGER, received_s REAL, process_rss_bytes REAL,
 payload_json TEXT, PRIMARY KEY(run_id,ordinal));
CREATE TABLE devices(run_id TEXT, ordinal INTEGER, device TEXT, temperature_c REAL, memory_bytes REAL, utilization_percent REAL,
 FOREIGN KEY(run_id,ordinal) REFERENCES samples(run_id,ordinal));
CREATE TABLE components(run_id TEXT REFERENCES runs, root TEXT, revision TEXT, dirty INTEGER);
CREATE TABLE metrics(run_id TEXT REFERENCES runs, kind TEXT, name TEXT, value_json TEXT);
CREATE TABLE evidence(run_id TEXT REFERENCES runs, kind TEXT, value_json TEXT);
CREATE TABLE gaps(run_id TEXT REFERENCES runs, code TEXT);
CREATE INDEX gaps_by_code ON gaps(code,run_id);
CREATE INDEX devices_by_run ON devices(run_id);
CREATE INDEX runs_by_created ON runs(created);
'''


def import_run(connection, folder, report_fn):
    rid = run_id(folder.name)
    before = identities(folder)
    if before['run.json'] is None or before['run.json']['bytes'] > 2 * 1024 * 1024:
        raise ValueError('Missing or oversized run metadata')
    run = decode((folder / 'run.json').read_bytes())
    if run['prompt_id'] != rid:
        raise ValueError('Run ID disagrees with directory')
    if run['status'] not in TERMINAL:
        raise ValueError('Run is active or has unsupported status')
    connection.execute('INSERT INTO runs VALUES (?,?,?,?,?,?,?,?)',
                       (rid, run['status'], run.get('label'), number(run.get('created')), None, 0, 0, '{}'))
    recent = collections.deque(maxlen=10000)
    event_count = sample_count = 0
    for event in json_lines(folder / 'events.jsonl'):
        connection.execute('INSERT INTO events VALUES (?,?,?,?)', (rid, event_count, event.get('type'), encoded(safe_numbers(event))))
        recent.append(event)
        event_count += 1
    for sample in json_lines(folder / 'samples.jsonl'):
        connection.execute('INSERT INTO samples VALUES (?,?,?,?,?)',
                           (rid, sample_count, number(sample.get('received')), number(sample.get('proc_rss')), encoded(safe_numbers(sample))))
        for device in sample.get('devices', []):
            connection.execute('INSERT INTO devices VALUES (?,?,?,?,?,?)',
                               (rid, sample_count, f"{device.get('type')}:{device.get('index')}", number(device.get('temperature')),
                                number(device.get('nvml_used')), number(device.get('gpu_util'))))
        sample_count += 1
    report = report_fn(run, list(recent), event_count > len(recent))
    gaps = list(report['data_quality']['gaps'])
    if sample_count != run.get('sample_count', 0):
        gaps.append('stored_sample_count_mismatch')
    for name in FILES[1:]:
        if before[name] is None:
            gaps.append('source_missing:' + name)
    report['index_quality_gaps'] = gaps
    report = safe_numbers(report)
    connection.execute('UPDATE runs SET wall_s=?,sample_count=?,event_count=?,report_json=? WHERE run_id=?',
                       (report['admitted_wall_seconds'], sample_count, event_count, encoded(report), rid))
    connection.executemany('INSERT INTO gaps VALUES (?,?)', ((rid, code) for code in set(gaps)))
    for phase, seconds in report['phase_seconds'].items():
        connection.execute('INSERT INTO metrics VALUES (?,?,?,?)', (rid, 'phase_seconds', phase, encoded(seconds)))
    for ordinal, sampler in enumerate(report['samplers']):
        connection.execute('INSERT INTO metrics VALUES (?,?,?,?)', (rid, 'sampler', str(ordinal), encoded(sampler)))
    for kind in ('resolved_primitive_inputs', 'runtime_evidence', 'configured_models', 'output_evidence', 'visual_reviews'):
        connection.execute('INSERT INTO evidence VALUES (?,?,?)', (rid, kind, encoded(report[kind])))
    provenance = run.get('provenance') or {}
    for component in provenance.get('snapshot', {}).get('components', []):
        connection.execute('INSERT INTO components VALUES (?,?,?,?)',
                           (rid, component['root'], component.get('commit'), component.get('dirty')))
    if identities(folder) != before:
        raise ValueError('Source changed during import')
    connection.executemany('INSERT INTO sources VALUES (?,?,?)', ((rid, name, encoded(value)) for name, value in before.items()))
    return before


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_index(source=DEFAULT_SOURCE, analysis=DEFAULT_ANALYSIS):
    source, analysis = Path(source).resolve(), Path(analysis).resolve()
    if analysis == source or source in analysis.parents:
        raise ValueError('Analysis output must be outside raw runs')
    report_fn, identity = analyzer()
    folders = sorted(source.iterdir())
    analysis.mkdir(parents=True, exist_ok=True)
    generations = analysis / 'generations'
    generations.mkdir(exist_ok=True)
    with (analysis / 'build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        generation = str(uuid4())
        pending = generations / (generation + '.pending')
        connection = sqlite3.connect(pending)
        manifest, skipped = {}, []
        try:
            connection.executescript(SQL)
            for folder in folders:
                connection.execute('SAVEPOINT one_run')
                try:
                    manifest[folder.name] = import_run(connection, folder, report_fn)
                except (ValueError, KeyError, TypeError, AttributeError, OSError, sqlite3.IntegrityError) as error:
                    connection.execute('ROLLBACK TO one_run')
                    skipped.append({'run_id': folder.name, 'reason': str(error)[:300]})
                finally:
                    connection.execute('RELEASE one_run')
            if not manifest:
                raise ValueError('No stable terminal runs; previous generation retained')
            for rid, expected in manifest.items():
                if identities(source / rid) != expected:
                    raise ValueError('Source changed before publication: ' + rid)
            if identity != analyzer_identity():
                raise ValueError('Analyzer changed before publication')
            metadata = {'schema': SCHEMA, 'generation': generation, 'created': time.time(), 'source': str(source),
                        'analyzer': identity, 'run_count': len(manifest), 'source_manifest_sha256': sha(manifest),
                        'skipped': skipped, 'source_directory_changed': folders != sorted(source.iterdir())}
            connection.execute('INSERT INTO metadata VALUES (?)', (encoded(metadata),))
            connection.commit()
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or connection.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Index integrity validation failed')
            connection.close()
            with pending.open('rb') as stream:
                os.fsync(stream.fileno())
            published = pending.with_suffix('.sqlite')
            pending.rename(published)
            sync_directory(generations)
            pointer = analysis / (generation + '.json')
            with pointer.open('x') as stream:
                stream.write(encoded({'generation': generation}) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            pointer.replace(analysis / 'current.json')
            sync_directory(analysis)
            return metadata
        finally:
            connection.close()
            pending.unlink(missing_ok=True)


class AnalysisIndex:
    def __init__(self, analysis=DEFAULT_ANALYSIS):
        analysis = Path(analysis).resolve()
        generation = run_id(decode((analysis / 'current.json').read_bytes())['generation'])
        self.path = analysis / 'generations' / (generation + '.sqlite')
        self.connection = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA query_only=ON')
        self.metadata = decode(self.connection.execute('SELECT value FROM metadata').fetchone()[0])
        if self.metadata['schema'] != SCHEMA or self.metadata['generation'] != generation:
            self.close()
            raise ValueError('Unsupported or inconsistent index metadata')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.connection.close()

    def _query(self, sql, params=()):
        deadline = time.monotonic() + 2
        self.connection.set_progress_handler(lambda: time.monotonic() > deadline, 1000)
        return [dict(row) for row in self.connection.execute(sql, params)]

    def list_runs(self, status=None, gap=None, limit=50):
        if not 1 <= limit <= 100:
            raise ValueError('Limit must be 1..100')
        return self._query('''SELECT run_id,status,label,created,wall_s,sample_count,event_count FROM runs
            WHERE (? IS NULL OR status=?) AND (? IS NULL OR run_id IN (SELECT run_id FROM gaps WHERE code=?))
            ORDER BY created DESC,run_id LIMIT ?''', (status, status, gap, gap, limit))

    def resources(self, rid):
        run_id(rid)
        return self._query('''SELECT (SELECT count(*) FROM samples WHERE run_id=?) AS stored_sample_count,
            (SELECT max(process_rss_bytes) FROM samples WHERE run_id=?) AS process_rss_max_bytes,
            max(temperature_c) AS gpu_temperature_max_c, max(memory_bytes) AS gpu_memory_max_bytes,
            max(utilization_percent) AS gpu_utilization_max_percent FROM devices WHERE run_id=?''', (rid, rid, rid))[0]

    def evidence(self, ids):
        if not 1 <= len(ids) <= 6 or len(set(ids)) != len(ids):
            raise ValueError('Select 1..6 distinct runs')
        if self.metadata['analyzer'] != analyzer_identity():
            raise ValueError('Analyzer changed; rebuild index')
        result = []
        for rid in ids:
            run_id(rid)
            rows = self._query('SELECT report_json FROM runs WHERE run_id=?', (rid,))
            if not rows:
                raise ValueError('Run is absent from index: ' + rid)
            expected = {row['name']: decode(row['identity_json']) for row in self._query('SELECT name,identity_json FROM sources WHERE run_id=?', (rid,))}
            if identities(Path(self.metadata['source']) / rid) != expected:
                raise ValueError('Source changed; rebuild index: ' + rid)
            result.append({'run_id': rid, 'source_files': expected, 'report': decode(rows[0]['report_json']), 'resources': self.resources(rid)})
        return result
