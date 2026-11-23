"""Objective-led comparisons calculated from Brain snapshots and native history."""
import argparse
import csv
import io
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from brain_index import AnalysisIndex, DEFAULT_ANALYSIS, decode, encoded, history_fingerprint, sha
from brain_reports import evidence_packet, save_bundle
from brain_local_model import generate


def execution_evidence(record, run_id, report):
    status = record.get('status', {}) if isinstance(record, dict) else {}
    expected = report.get('generation_fingerprint')
    if (not isinstance(status, dict) or not expected or report.get('status') != 'succeeded'
            or status.get('completed') is not True or status.get('status_str') != 'success'):
        return None
    try:
        _, native_id, graph, extra, targets = record['prompt'][:5]
        if native_id != run_id or history_fingerprint(graph, extra, targets) != expected:
            return None
    except (KeyError, TypeError, AttributeError, ValueError):
        return None
    times = {}
    messages = status.get('messages')
    if not isinstance(messages, list):
        return None
    for message in messages:
        if not isinstance(message, (list, tuple)) or len(message) != 2 or not isinstance(message[1], dict):
            return None
        kind, data = message
        if data.get('prompt_id') != run_id:
            continue
        if kind in ('execution_error', 'execution_interrupted'):
            return None
        if kind in ('execution_start', 'execution_success'):
            value = data.get('timestamp')
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                times.setdefault(kind, []).append(value)
    if any(len(times.get(kind, [])) != 1 for kind in ('execution_start', 'execution_success')):
        return None
    start, end = times['execution_start'][0], times['execution_success'][0]
    if end < start:
        return None
    return {'generation_fingerprint': expected, 'started_ms': start, 'succeeded_ms': end}


def comparison(packet, objective, history):
    if not objective.strip():
        raise ValueError('Supply the production objective')
    rows = []
    timing = {}
    for run in packet['runs']:
        report = run['report']
        run_id = run['run_id']
        evidence = execution_evidence(history.get(run_id, {}), run_id, report)
        if evidence is not None:
            timing[run_id] = evidence
        seconds = (evidence['succeeded_ms'] - evidence['started_ms']) / 1000 if evidence else None
        rows.append({'run_id': run['run_id'], 'brain_status': report.get('status') or 'unknown', 'execution_seconds': seconds,
                     'admitted_seconds': report.get('admitted_wall_seconds'),
                     'sampling_seconds': report.get('phase_seconds', {}).get('Sampling'),
                     'phase_seconds': report.get('phase_seconds', {}),
                     'gpu_peak_c': run['resources'].get('gpu_temperature_max_c'),
                     'vram_peak_gib': (report.get('peaks', {}).get('cuda:0.nvml_used') or 0) / 2**30 if report.get('peaks', {}).get('cuda:0.nvml_used') is not None else None,
                     'ram_peak_gib': report.get('peaks', {}).get('ram_used') / 2**30 if report.get('peaks', {}).get('ram_used') is not None else None,
                     'cached_nodes': report.get('cached_nodes', []),
                     'visual_verdict': 'See attributed review; no automatic acceptance'})
    baseline = rows[0]['execution_seconds']
    for row in rows:
        value = row['execution_seconds']
        row['execution_difference_percent'] = (value / baseline - 1) * 100 if baseline and value is not None else None
    return {'objective': objective, 'rows': rows, 'history_sha256': sha(history), 'native_timing': timing,
            'basis': 'Brain status is the recorded outcome, not independent native verification. Native execution timestamps match successful indexed generations; observed differences are not causal speedups. Missing is not zero.',
            'parameter_differences': [d for d in packet['differences'] if any(d['field'].startswith('/' + k) for k in ('configured_models', 'resolved_primitive_inputs', 'runtime_settings', 'runtime_evidence', 'cached_nodes'))],
            'visual_reviews': {r['run_id']: r['report'].get('visual_reviews', {}) for r in packet['runs']}}


def chart(data):
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), layout='constrained')
    labels = [f"{r.get('label', r['run_id'][:8])}\n({r['brain_status']})" for r in data['rows']]
    for ax, key, title in zip(axes.flat, ['execution_seconds', 'sampling_seconds', 'vram_peak_gib', 'ram_peak_gib'],
                             ['Execution (seconds; excludes queue)', 'Sampling (seconds)', 'GPU memory peak (GiB)', 'System RAM peak (GiB)']):
        for i, row in enumerate(data['rows']):
            value = row[key]
            if value is None:
                ax.text(i, 0, 'Unavailable', ha='center', va='bottom', fontsize=9)
            else:
                ax.bar(i, value, color='#3578a8')
                ax.text(i, value, f'{value:.2f}', ha='center', va='bottom', fontsize=9)
        ax.set_xticks(range(len(labels)), labels)
        ax.set_xlim(-.6, len(labels) - .4)
        ax.set_title(title)
        ax.set_ylim(bottom=0)
        ax.margins(y=.18)
    fig.suptitle('Observed recipe costs — not a qualified model ranking')
    output = io.StringIO()
    fig.savefig(output, format='svg')
    plt.close(fig)
    return output.getvalue()


def phase_chart(data):
    phases = ['Conditioning / encoding', 'Sampling', 'Decoding']
    fig, ax = plt.subplots(figsize=(10, 4), layout='constrained')
    count = len(data['rows'])
    for i, row in enumerate(data['rows']):
        for j, phase in enumerate(phases):
            x = j + i / (count + 1)
            value = row['phase_seconds'].get(phase)
            if value is None:
                ax.text(x, 0, 'N/A', ha='center', va='bottom', fontsize=8)
            else:
                ax.bar(x, value, width=.8 / (count + 1), color=f'C{i}',
                       label=row.get('label', row['run_id'][:8]) if j == 0 else None)
    ax.set_xticks([j + (count - 1) / (2 * (count + 1)) for j in range(3)], phases)
    ax.set_ylabel('Observed seconds')
    ax.set_title('Phase costs — N/A means missing or incomplete, never zero')
    ax.legend()
    output = io.StringIO()
    fig.savefig(output, format='svg')
    plt.close(fig)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_ids', nargs='+')
    parser.add_argument('--objective', required=True)
    parser.add_argument('--labels', nargs='+', help='Optional display labels in run order')
    parser.add_argument('--history', type=Path, help='Exported native /history JSON; omitted timings remain unavailable')
    parser.add_argument('--model', help='Optional already-loaded local model alias')
    parser.add_argument('--endpoint', default='http://127.0.0.1:9931')
    parser.add_argument('--analysis', type=Path, default=DEFAULT_ANALYSIS)
    args = parser.parse_args()
    if args.history and args.history.stat().st_size > 8 * 1024 * 1024:
        parser.error('History export exceeds 8 MiB')
    history = decode(args.history.read_bytes()) if args.history else {}
    with AnalysisIndex(args.analysis) as index:
        packet = evidence_packet(index, args.run_ids)
        data = comparison(packet, args.objective, history)
        if args.labels:
            if len(args.labels) != len(data['rows']):
                parser.error('Provide one label per run')
            for row, label in zip(data['rows'], args.labels):
                row['label'] = label
        packet['objective'] = args.objective
        for run, row in zip(packet['runs'], data['rows']):
            run['report']['calculated_comparison'] = row
        csv_file = io.StringIO()
        writer = csv.DictWriter(csv_file, fieldnames=list(data['rows'][0]))
        writer.writeheader()
        writer.writerows(data['rows'])
        lines = ['# Production comparison', '', args.objective, '', data['basis'], '',
                 '| Recipe | Brain status | Execution s | Difference % | Sampling s | VRAM GiB | RAM GiB | GPU peak °C |',
                 '|---|---|---:|---:|---:|---:|---:|---:|']
        for row in data['rows']:
            values = [row.get('label', row['run_id'][:8]), row['brain_status']] + [row[k] for k in
                      ('execution_seconds', 'execution_difference_percent', 'sampling_seconds', 'vram_peak_gib', 'ram_peak_gib', 'gpu_peak_c')]
            lines.append('| ' + ' | '.join('Unavailable' if v is None else f'{v:.2f}' if isinstance(v, float) else str(v).replace('|', '/') for v in values) + ' |')
        lines += ['', '![Measured costs](comparison.svg)', '', '![Phase costs](phases.svg)', '',
                  '## Model and parameter evidence', '',
                  'Full field differences and cache state are retained in comparison.json. These are recorded settings, not proof of loaded weights.']
        for run, row in zip(packet['runs'], data['rows']):
            lines += ['', row.get('label', run['run_id']), '', '```json',
                      encoded({'models': run['report'].get('configured_models'), 'cached_nodes': row['cached_nodes'],
                               'runtime_settings': run['report'].get('runtime_settings')}).replace('`', '\\u0060'), '```']
        lines += ['', '## Reviewer findings', '', 'No automatic visual verdict or production acceptance.']
        for run_id, reviews in data['visual_reviews'].items():
            for output_hash, review in reviews.items():
                lines += ['', f"Run {run_id}; output {output_hash}; reviewer {review.get('reviewer')}", '',
                          '```json', encoded(review.get('findings', {})).replace('`', '\\u0060'), '```']
        advisory = generate(packet, args.endpoint, args.model, runtime='llama.cpp') if args.model else None
        if advisory:
            lines += ['', '## Unverified local explanation', '', '```json', encoded(advisory['interpretation']).replace('`', '\\u0060'), '```']
        index.evidence(args.run_ids)
        target = save_bundle(args.analysis, 'comparisons', {'comparison.json': data, 'packet.json': packet,
                             'advisor.json': advisory, 'comparison.csv': csv_file.getvalue(),
                             'comparison.svg': chart(data), 'phases.svg': phase_chart(data), 'report.md': '\n'.join(lines)})
    print(encoded({'comparison': str(target)}))


if __name__ == '__main__':
    main()
