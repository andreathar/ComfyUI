"""On-demand Brain analysis. Run with the project Python, no server needed."""
import argparse
import sys
from pathlib import Path

from brain_index import AnalysisIndex, DEFAULT_ANALYSIS, DEFAULT_SOURCE, build_index, decode, encoded
from brain_local_model import ModelResponseError, endpoint, generate
from brain_reports import create_experiment, evidence_packet, record_decision, save_failure, save_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, default=DEFAULT_ANALYSIS)
    commands = parser.add_subparsers(dest='command', required=True)
    rebuild = commands.add_parser('index', help='Publish a new stable snapshot; keep previous generations')
    rebuild.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    listing = commands.add_parser('runs', help='List indexed observations; rebuild before fresh reports')
    listing.add_argument('--status')
    listing.add_argument('--gap')
    listing.add_argument('--limit', type=int, default=50)
    for command in ('report', 'experiment'):
        selected = commands.add_parser(command)
        selected.add_argument('run_ids', nargs='+', help='Baseline first, then candidates; at most six')
        if command == 'report':
            selected.add_argument('--model', help='Installed LM Studio model; omit for deterministic report')
            selected.add_argument('--endpoint', default='http://127.0.0.1:1234')
            selected.add_argument('--allow-load', action='store_true', help='Explicitly allow selected installed model JIT loading')
        else:
            selected.add_argument('--hypothesis', required=True)
            selected.add_argument('--changed-field', action='append', required=True)
            selected.add_argument('--controls', type=Path, required=True, help='JSON object describing controlled and unknown conditions')
    decision = commands.add_parser('decision', help='Record an explicit human decision; never applies settings')
    decision.add_argument('experiment_id')
    decision.add_argument('--value', choices=['inconclusive', 'reject', 'test_further', 'adopt'], required=True)
    decision.add_argument('--reviewer', required=True)
    decision.add_argument('--rationale', required=True)
    args = parser.parse_args()
    if args.command == 'report' and args.model:
        try:
            args.endpoint = endpoint(args.endpoint)
        except ValueError:
            parser.error('Use an explicit HTTP loopback endpoint without credentials or paths')
    if args.command == 'index':
        result = build_index(args.source, args.analysis)
    elif args.command == 'decision':
        result = {'decision': str(record_decision(args.analysis, args.experiment_id, args.value, args.reviewer, args.rationale))}
    else:
        with AnalysisIndex(args.analysis) as index:
            if args.command == 'runs':
                result = {'snapshot': index.metadata, 'freshness': 'snapshot only; reports revalidate selected sources',
                          'runs': index.list_runs(args.status, args.gap, args.limit)}
            else:
                packet = evidence_packet(index, args.run_ids)
                if args.command == 'experiment':
                    if args.controls.stat().st_size > 8192:
                        parser.error('Controls file exceeds 8 KiB')
                    result = {'experiment': str(create_experiment(args.analysis, packet, args.hypothesis,
                                                   args.changed_field, decode(args.controls.read_bytes())))}
                else:
                    try:
                        model_result = generate(packet, args.endpoint, args.model, args.allow_load) if args.model else None
                    except (OSError, ValueError) as error:
                        failure = save_failure(args.analysis, packet, args.model, args.endpoint, error,
                                               error.details if isinstance(error, ModelResponseError) else None)
                        print(encoded({'error': str(error), 'failed_report': str(failure)}), file=sys.stderr)
                        return 1
                    # A model request can take time; reject a source change before publishing its report.
                    index.evidence(args.run_ids)
                    result = {'report': str(save_report(args.analysis, packet, model_result))}
    print(encoded(result))


if __name__ == '__main__':
    sys.exit(main())
