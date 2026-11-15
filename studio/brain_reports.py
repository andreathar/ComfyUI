"""Pinned evidence, deterministic comparisons, and human experiment records."""
import os
from pathlib import Path
import shutil
import time
from uuid import uuid4

from brain_index import decode, encoded, run_id, safe_numbers, sha, sync_directory

MAX_PACKET_BYTES = 64 * 1024
REPORT_FIELDS = ('status', 'coverage', 'data_quality', 'index_quality_gaps', 'resolved_primitive_inputs',
                 'runtime_evidence', 'runtime_settings', 'configured_models', 'generation_fingerprint',
                 'admitted_wall_seconds', 'phase_seconds', 'samplers', 'cached_nodes', 'sample_count',
                 'peaks', 'output_evidence', 'visual_reviews', 'provenance')
RULES = ['Unknown is not zero. Sampled peaks are not continuous measurements.',
         'Configured inputs and native output attestations have different evidence strength.',
         'Matching parameters alone does not prove fair comparison, reproducibility or causality.',
         'Historical source snapshots do not prove the code loaded by the running server.',
         'No automatic ranking, baseline adoption, model loading or parameter changes.',
         'Model prose is an unverified interpretation requiring human review.']


def flatten(value, prefix=''):
    if isinstance(value, dict) and value:
        result = {}
        for key, item in value.items():
            escaped = key.replace('~', '~0').replace('/', '~1')
            result.update(flatten(item, prefix + '/' + escaped))
        return result
    return {prefix: value}


def evidence_packet(index, ids):
    records = index.evidence(ids)
    runs = [{**record, 'report': {k: record['report'].get(k) for k in REPORT_FIELDS}} for record in records]
    differences = []
    baseline = flatten(runs[0]['report'])
    for candidate in runs[1:]:
        fields = flatten(candidate['report'])
        for key in sorted(baseline.keys() | fields.keys()):
            if key not in baseline or key not in fields or baseline[key] != fields[key]:
                differences.append({'run_id': candidate['run_id'], 'field': key,
                                    'baseline_present': key in baseline, 'candidate_present': key in fields,
                                    'baseline': baseline.get(key), 'candidate': fields.get(key)})
    generation = {k: v for k, v in index.metadata.items() if k != 'skipped'}
    generation['skipped_count'] = len(index.metadata.get('skipped', []))
    packet = safe_numbers({'schema': 'brain-evidence.v1', 'generated_at': time.time(),
                          'generation': generation, 'runs': runs, 'differences': differences,
                          'benchmark_qualified': False, 'rules': RULES})
    if len(encoded(packet).encode()) > MAX_PACKET_BYTES:
        raise ValueError('Evidence packet exceeds 64 KiB; select fewer runs')
    return packet


def write_json(path, value):
    with path.open('x') as stream:
        stream.write(encoded(value) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def save_bundle(analysis, category, files):
    root = Path(analysis) / category
    root.mkdir(parents=True, exist_ok=True)
    identifier = str(uuid4())
    pending = root / ('.' + identifier)
    pending.mkdir()
    try:
        for name, value in files.items():
            if name.endswith('.json'):
                write_json(pending / name, value)
            else:
                with (pending / name).open('x') as stream:
                    stream.write(value)
                    stream.flush()
                    os.fsync(stream.fileno())
        target = root / identifier
        sync_directory(pending)
        pending.rename(target)
        sync_directory(root)
        return target
    finally:
        if pending.exists():
            shutil.rmtree(pending)


def save_report(analysis, packet, model_result=None):
    result = {'schema': 'brain-report.v1', 'created': time.time(), 'packet_sha256': sha(packet),
              'benchmark_qualified': False, 'human_review': 'pending', 'model': model_result}
    lines = ['# Brain evidence report', '', 'Evidence packet SHA-256: `' + result['packet_sha256'] + '`', '',
             'These observations are not a qualified benchmark or a production adoption decision.', '',
             '| Run | Status | Wall seconds | Stored samples | GPU peak °C |',
             '|---|---|---:|---:|---:|']
    for run in packet['runs']:
        report = run['report']
        values = [run['run_id'], report['status'], report['admitted_wall_seconds'], run['resources']['stored_sample_count'],
                  run['resources']['gpu_temperature_max_c']]
        lines.append('| ' + ' | '.join('unknown' if v is None else str(v) for v in values) + ' |')
    lines += ['', '## Evidence gaps', '']
    for run in packet['runs']:
        lines.append('- `' + run['run_id'] + '`: ' + ', '.join(run['report']['index_quality_gaps']))
    lines += ['', '## Observed differences', '',
              str(len(packet['differences'])) + ' differing evidence fields. See packet.json for exact values and missing-field indicators.',
              'Differences include outcomes and coverage; they are not all experimental interventions.', '', '## Interpretation', '']
    if model_result:
        lines += ['Unverified local-model output follows as quoted data. Citations were checked for existence, not truth.', '',
                  '```json', encoded(model_result['interpretation']).replace('`', '\\u0060'), '```']
    else:
        lines.append('No local model was invoked. Collect matched repeated trials and resolve evidence gaps before recommending an adoption.')
    lines += ['', *('- ' + rule for rule in RULES), '']
    return save_bundle(analysis, 'reports', {'packet.json': packet, 'report.json': result, 'report.md': '\n'.join(lines)})


def create_experiment(analysis, packet, hypothesis, changed_fields, controls):
    if not isinstance(hypothesis, str) or not 1 <= len(hypothesis) <= 1000:
        raise ValueError('Hypothesis must be 1..1000 characters')
    if len(packet['runs']) < 2:
        raise ValueError('An experiment needs baseline and candidate runs')
    observed = {d['field'] for d in packet['differences']}
    if not isinstance(changed_fields, list) or not changed_fields or any(f not in observed for f in changed_fields):
        raise ValueError('Changed fields must identify observed packet difference paths')
    if not isinstance(controls, dict) or len(encoded(controls)) > 8000:
        raise ValueError('Controls must be a JSON object of at most 8000 characters')
    experiment = {'schema': 'brain-experiment.v1', 'created': time.time(), 'hypothesis': hypothesis,
                  'baseline_run_id': packet['runs'][0]['run_id'], 'candidate_run_ids': [r['run_id'] for r in packet['runs'][1:]],
                  'intended_changed_fields': changed_fields, 'controls': safe_numbers(controls),
                  'other_differing_fields': sorted(observed - set(changed_fields)),
                  'packet_sha256': sha(packet), 'generation': packet['generation']['generation'],
                  'repeated_trials': 'not established; group and review selected run IDs explicitly', 'decision': 'pending'}
    return save_bundle(analysis, 'experiments', {'experiment.json': experiment, 'packet.json': packet})


def record_decision(analysis, experiment_id, decision, reviewer, rationale):
    run_id(experiment_id)
    if decision not in ('inconclusive', 'reject', 'test_further', 'adopt'):
        raise ValueError('Unsupported human decision')
    if not isinstance(reviewer, str) or not 1 <= len(reviewer) <= 200 or not isinstance(rationale, str) or not 1 <= len(rationale) <= 4000:
        raise ValueError('Reviewer and rationale are required and bounded')
    folder = Path(analysis) / 'experiments' / experiment_id
    experiment = decode((folder / 'experiment.json').read_bytes())
    packet = decode((folder / 'packet.json').read_bytes())
    if sha(packet) != experiment['packet_sha256']:
        raise ValueError('Experiment evidence hash mismatch')
    value = {'schema': 'brain-decision.v1', 'experiment_id': experiment_id, 'created': time.time(),
             'experiment_sha256': sha(experiment), 'packet_sha256': experiment['packet_sha256'],
             'decision': decision, 'reviewer': reviewer, 'rationale': rationale,
             'effect': 'Recorded human decision only; no workflow or baseline configuration changed'}
    path = folder / ('decision-' + str(uuid4()) + '.json')
    pending = folder / ('.' + path.name)
    try:
        write_json(pending, value)
        pending.rename(path)
        sync_directory(folder)
    finally:
        pending.unlink(missing_ok=True)
    return path


def save_failure(analysis, packet, model, origin, error, details=None):
    failure = {'schema': 'brain-report-failure.v1', 'created': time.time(), 'packet_sha256': sha(packet),
               'model': model, 'endpoint': origin, 'error_type': type(error).__name__, 'error': str(error)[:1000],
               'status': 'failed; no valid interpretation published', 'response_diagnostics': details}
    return save_bundle(analysis, 'failed_reports', {'packet.json': packet, 'failure.json': failure})
