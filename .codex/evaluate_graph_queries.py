"""Read-only CBM production probes; save observations without hiding graph gaps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import threading
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
CLI = '/home/athar/.local/bin/codebase-memory-mcp'


def memory_sample():
    rss = 0
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if os.readlink(entry / 'exe') != CLI:
                continue
            for line in (entry / 'status').read_text().splitlines():
                if line.startswith('VmRSS:'):
                    rss += int(line.split()[1]) * 1024
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    mem = dict((line.split(':')[0], int(line.split()[1]) * 1024)
               for line in Path('/proc/meminfo').read_text().splitlines())
    return rss, mem['MemAvailable'], mem['SwapTotal'] - mem['SwapFree']


def run_query(tool, arguments, output, label):
    command = [CLI, 'cli', tool]
    for key, value in arguments.items():
        command.extend(['--' + key.replace('_', '-'),
                        json.dumps(value) if isinstance(value, (list, bool)) else str(value)])
    started = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
        elapsed = time.perf_counter() - started
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        stdout = (exc.stdout or b'').decode() if isinstance(exc.stdout, bytes) else exc.stdout or ''
        stderr = 'Query exceeded 20 second client timeout; no shared process was stopped.'
        code = 124
    (output / (label + '.json')).write_text(stdout)
    (output / (label + '.stderr')).write_text(stderr)
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = {'error': 'No JSON response'}
    failed = code != 0 or data.get('isError') is True or bool(data.get('error'))
    return {'command': command, 'seconds': elapsed, 'exit': code,
            'query_failed': failed, 'result_file': label + '.json'}, data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, choices=range(1, 6), default=3)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT / '.codex/graph-questions.json').read_text())
    owners = {row['owner']: row for row in manifest['owners']}
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'owners': [],
              'sources': [], 'probes': [], 'operational_errors': [], 'freshness_issues': []}
    metadata, projects = run_query('list_projects', {'format': 'json'}, args.output, 'projects')
    available = {p['name']: p['root_path'] for p in projects.get('projects', [])}
    if metadata['query_failed'] or projects.get('has_more'):
        raise RuntimeError('Project inventory failed or is paginated; resolve before probing.')
    for owner, row in owners.items():
        if available.get(row['project']) != row['canonical_root']:
            raise RuntimeError('Missing or mismatched graph owner: ' + owner)
        head = subprocess.check_output(['git', '-C', row['canonical_root'], 'rev-parse', 'HEAD'], text=True).strip()
        label = 'owner-' + str(len(report['owners']))
        status_call, status = run_query('index_status', {'project': row['project'], 'verbose': True, 'format': 'json'}, args.output, label)
        paths = sorted({e['file'] for q in manifest['questions'] for e in q['evidence'] if e['owner'] == owner})
        coverage_call, coverage = run_query('check_index_coverage', {
            'project': row['project'], 'paths': paths, 'diagnostics': 'full', 'format': 'json'}, args.output, label + '-coverage')
        indexed_head = status.get('git', {}).get('head_sha')
        if indexed_head != head:
            report['freshness_issues'].append(owner + ': reported HEAD mismatch or unavailable')
        if any(p.get('freshness') != 'metadata_match' for p in coverage.get('paths', [])):
            report['freshness_issues'].append(owner + ': file metadata changed or unavailable')
        if len(coverage.get('paths', [])) != len(paths):
            report['freshness_issues'].append(owner + ': incomplete file coverage response')
        report['owners'].append({'owner': owner, 'head': head, 'reported_head': indexed_head,
                                 'head_matches': head == indexed_head, 'coverage': coverage.get('paths', [])})
        if status_call['query_failed'] or coverage_call['query_failed']:
            report['operational_errors'].append(label)
    for question in manifest['questions']:
        for source in question['evidence']:
            path = Path(owners[source['owner']]['canonical_root']) / source['file']
            contents = path.read_bytes()
            report['sources'].append({'question': question['id'], 'owner': source['owner'],
                'file': source['file'], 'hash_matches': hashlib.sha256(contents).hexdigest() == source['sha256'],
                'anchors_present': all(a['text'] in contents.decode() for a in source['anchors'])})
    if not all(s['hash_matches'] and s['anchors_present'] for s in report['sources']):
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        raise RuntimeError('Source evidence changed; review facts and hashes before probing.')
    resources = {'peak_cbm_rss_bytes': 0, 'minimum_available_bytes': memory_sample()[1], 'peak_swap_bytes': 0}
    stop = threading.Event()

    def sample():
        while not stop.is_set():
            rss, available_ram, swap = memory_sample()
            resources['peak_cbm_rss_bytes'] = max(resources['peak_cbm_rss_bytes'], rss)
            resources['minimum_available_bytes'] = min(resources['minimum_available_bytes'], available_ram)
            resources['peak_swap_bytes'] = max(resources['peak_swap_bytes'], swap)
            stop.wait(.1)

    sampler = threading.Thread(target=sample)
    sampler.start()
    try:
        for question in manifest['questions']:
            for probe in question['queries']:
                observations = []
                for repeat in range(args.repeats):
                    call, data = run_query(probe['tool'], {
                        'project': owners[probe['owner']]['project'], **probe['arguments']},
                        args.output, probe['id'] + '-' + str(repeat + 1))
                    row_text = json.dumps(data.get('rows', []))
                    call['missing_row_fragments'] = [s for s in probe['required_row_fragments'] if s not in row_text]
                    call['rows'] = data.get('returned')
                    call['truncated'] = bool(data.get('truncated') or data.get('has_more'))
                    call['coverage'] = data.get('paths')
                    observations.append(call)
                result = {'question': question['id'], 'probe': probe['id'], 'observations': observations,
                          'median_seconds': statistics.median(r['seconds'] for r in observations)}
                report['probes'].append(result)
                print(probe['id'], 'median', round(result['median_seconds'], 3),
                      'missing', observations[-1]['missing_row_fragments'], flush=True)
    finally:
        stop.set()
        sampler.join()
        for question in manifest['questions']:
            for source in question['evidence']:
                path = Path(owners[source['owner']]['canonical_root']) / source['file']
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
                    report['freshness_issues'].append(str(path) + ': source changed during queries')
        for owner in report['owners']:
            head = subprocess.check_output(['git', '-C', owners[owner['owner']]['canonical_root'],
                                            'rev-parse', 'HEAD'], text=True).strip()
            if head != owner['head']:
                report['freshness_issues'].append(owner['owner'] + ': HEAD changed during queries')
        report['resources'] = resources
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    errors = report['operational_errors'] or report['freshness_issues'] or any(o['query_failed'] or o['truncated']
        for p in report['probes'] for o in p['observations'])
    # Missing relationships are findings, not failed tool calls or proof of dead code.
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
