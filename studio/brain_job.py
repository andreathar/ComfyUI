"""Report worker for an isolated native WorkflowBrainAnalysis queue job."""
import argparse
import ctypes
import os
from pathlib import Path
import signal
import sys

from brain_index import AnalysisIndex, build_index, decode, encoded, run_id
from brain_local_model import ModelResponseError, check_queue, generate, request_json
from brain_reports import evidence_packet, save_failure, save_report

ORIGIN = 'http://127.0.0.1:9931'
MODEL = 'brain-qwen35-9b'


def bind_parent(expected):
    if os.getppid() != expected:
        raise RuntimeError('Analysis parent changed before worker initialization')
    if sys.platform != 'linux':
        raise RuntimeError('Owned report workers currently require Linux parent-death signaling')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'Cannot bind report worker lifetime')
    if os.getppid() != expected:
        raise RuntimeError('Analysis parent exited during worker initialization')


def analyze(source_id, job_id, source, analysis):
    run_id(source_id)
    run_id(job_id)
    raw = decode((Path(source) / source_id / 'run.json').read_bytes())
    if (raw.get('status') in ('queued', 'running') or raw.get('evidence_status') in ('pending', 'collecting')
            or (raw.get('provenance') or {}).get('status') in ('pending', 'collecting')):
        raise ValueError('Source evidence and provenance must be settled')
    if raw.get('recording_error'):
        raise ValueError('Source recording failed; inspect it before analysis')
    build_index(source, analysis)
    with AnalysisIndex(analysis) as index:
        packet = evidence_packet(index, [source_id])
        report = packet['runs'][0]['report']
        model_result = None
        policy = 'deterministic: no successful observed sampling'
        try:
            if report['status'] == 'succeeded' and (report['phase_seconds'].get('Sampling') or 0) > 0:
                policy = 'local model interpretation of successful observed sampling'
                props = request_json(ORIGIN, '/props')
                model_path = Path(props['model_path'])
                stat = model_path.stat()
                identity = {'server_build': props.get('build_info'), 'model_path': str(model_path),
                            'model_bytes': stat.st_size, 'model_mtime_ns': str(stat.st_mtime_ns),
                            'identity_limit': 'path and stat are not a loaded-weight hash attestation'}
                model_result = generate(packet, ORIGIN, MODEL, runtime='llama.cpp', owned_job=(job_id, source_id))
                model_result['runtime_identity'] = identity
            index.evidence([source_id])
            target = save_report(analysis, packet, model_result)
        except (OSError, ValueError, KeyError) as error:
            failure = save_failure(analysis, packet, MODEL, ORIGIN, error,
                                   error.details if isinstance(error, ModelResponseError) else None)
            return {'status': 'failed', 'failure_id': failure.name, 'error': str(error)[:500]}
    return {'status': 'complete', 'report_id': target.name, 'policy': policy}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--parent-pid', type=int, required=True)
    args = parser.parse_args()
    bind_parent(args.parent_pid)
    check_queue(request_json('http://127.0.0.1:8188', '/queue'), (args.job_id, args.run_id))
    print(encoded(analyze(args.run_id, args.job_id, args.source, args.analysis)))


if __name__ == '__main__':
    main()
