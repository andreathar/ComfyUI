"""Inspect Studio storage or rehearse recovery of one project and one approved take."""

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain_index import AnalysisIndex, FILES, TERMINAL, build_index
from h3_manifest import file_digest
from master_take import prompt_digest, verify_inputs
from studio import production_bootstrap, production_references, production_store

PROJECTS = Path('studio/projects')
TAKES = Path('user/master_studio/takes')
STORY = Path('user/studio_storyboard')
BRAIN = Path('user/workflow_monitor')
SUITE = Path('output/h3_projects')
DATABASE = Path('user/comfyui.db')
RECORD_ERRORS = (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, sqlite3.Error)


def read(path):
    return json.loads(path.read_bytes())


def files(directory):
    return sorted(p for p in directory.rglob('*') if not p.is_symlink() and p.is_file()
                  and p.resolve() == p)


def relative_path(root, value, original=None):
    """Translate locators in receipts into contained, portable checkout paths."""
    path = Path(value)
    if path.is_absolute():
        path = path.relative_to(original or root)
    if not path.parts or '..' in path.parts or (root / path).resolve() != root / path:
        raise ValueError('Path escapes the selected checkout or uses a symlink')
    return path


def open_db(path):
    connection = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
    connection.execute('PRAGMA query_only = ON')
    return closing(connection)


def database_checks(path):
    with open_db(path) as connection:
        return {'integrity': connection.execute('PRAGMA quick_check').fetchone()[0],
                'foreign_key_violations': len(connection.execute('PRAGMA foreign_key_check').fetchall())}


def project_rows(root):
    jobs = {}
    for file in sorted((root / STORY / 'jobs').glob('*/proposal.json')):
        try:
            if file.resolve() == file:
                value = read(file)
                if value.get('job_id') == file.parent.name and 'document' in value:
                    jobs[file.parent.name] = value['document']
        except RECORD_ERRORS:
            continue
    rows = []
    for directory in sorted((root / PROJECTS).glob('*')):
        if directory.is_symlink() or not directory.is_dir():
            continue
        row = {'path': str(directory.relative_to(root)), 'owner': 'Storyboard'}
        try:
            if (directory / 'project.json').exists():
                snapshot = production_store.read_project(directory)
                manifest = snapshot['manifest']
                bank = production_references.bank(snapshot, {kind: root / kind for kind in ('input', 'output')})
                matches = []
                for identifier, document in jobs.items():
                    try:
                        digest = production_bootstrap.preview(document, directory.name)['digest']
                        if digest == manifest['proposal_digest']:
                            matches.append(identifier)
                    except RECORD_ERRORS:
                        continue
                initial = directory / manifest['reference_plan']
                reference_status = 'missing'
                if initial.resolve() == initial and initial.is_file():
                    reference_status = ('matches_current' if read(initial) == production_bootstrap.reference_requirements(
                        snapshot['production']) else 'creation_snapshot_differs')
                row.update(status='current', code=manifest['code'], revision=snapshot['revision'],
                           shots=[shot['id'] for shot in snapshot['production']['shots']],
                           creation_reference_plan=reference_status,
                           creation_job={'status': 'ambiguous' if len(matches) > 1 else
                                         'content_match' if matches else 'unlinked', 'candidates': matches},
                           references=[
                               {'key': need['key'], 'role': need['role'], 'shots': need['shots'], 'status': need['status'],
                                **({'loader_path': need['binding']['loader_path'],
                                    'sha256': need['binding']['source_sha256']} if 'binding' in need else {})}
                               for need in bank['requirements']
                           ])
            else:
                docs = [p for p in files(directory) if p.name == 'production.json']
                legacy = []
                for doc in docs:
                    data = read(doc)
                    legacy.append({'path': str(doc.relative_to(root)), 'code': data['project']['code'],
                                   'shots': [shot['id'] for shot in data['shots']]})
                if legacy:
                    row.update(status='legacy_production', documents=legacy)
                elif any(p.name == 'assets.json' for p in files(directory)):
                    row.update(status='reference_lab')
                else:
                    continue
        except RECORD_ERRORS as error:
            row.update(status='invalid_record', detail=str(error))
        rows.append(row)
    return rows


def take_row(root, path, projects=(), original=None):
    row = {'path': str(path.relative_to(root)), 'owner': 'Master Studio', 'checks': {}}
    checks = row['checks']

    def check(name, status, owner, **details):
        checks[name] = {'status': status, 'owner': owner, **details}

    def artifact(name, owner, record, field, digest_field=None):
        if not record.get(field):
            check(name, 'missing_locator', owner)
            return None
        locator = relative_path(root, record[field], original)
        file = root / locator
        status = 'present'
        details = {'path': str(locator)}
        if not file.is_file():
            status = 'missing'
        else:
            details['bytes'] = file.stat().st_size
            if digest_field:
                digest = file_digest(file)
                status = 'verified' if digest == record.get(digest_field) else 'changed'
                details.update(hash_algorithm='sha256', recorded_digest=record.get(digest_field))
        check(name, status, owner, **details)
        return file if file.is_file() else None

    try:
        state = read(path / 'take.json')
        row.update({key: state.get(key) for key in ('project', 'scene_id', 'shot_id', 'take_id', 'status',
                                                   'prompt_id', 'prompt_sha256', 'package_revision')})
        matches = []
        for project in projects:
            candidates = project.get('documents', [project])
            matches.extend({'path': candidate['path'], 'revision': candidate.get('revision')}
                           for candidate in candidates if candidate.get('code') == state.get('project')
                           and state.get('shot_id') in candidate.get('shots', ()))
        check('production_shot', 'linked_by_shot_id' if len(matches) == 1 else 'ambiguous' if matches else 'unlinked',
              'Storyboard', candidates=matches)
        if state['status'] == 'input_rejected' and not state.get('prompt_id'):
            check('execution', 'intentionally_skipped', 'Master Studio')
            return row

        try:
            verify_inputs(path, state)
            check('frozen_inputs', 'verified', 'Master Studio')
        except RECORD_ERRORS as error:
            check('frozen_inputs', 'missing' if isinstance(error, FileNotFoundError) else 'changed',
                  'Master Studio', detail=str(error))
        frozen_file = path / 'prompt.json'
        frozen = read(frozen_file) if frozen_file.is_file() else None
        history_file = path / 'history.json'
        native_output = None
        if history_file.is_file():
            archived = read(history_file)
            history = archived['prompt']
            matches_history = (frozen is not None and history[1] == state.get('prompt_id')
                               and prompt_digest(frozen) == prompt_digest(history[2])
                               and archived['status']['status_str'] == 'success' and archived['status']['completed'] is True)
            check('history', 'verified' if matches_history else 'changed', 'Master Studio',
                  path=str(history_file.relative_to(root)))
            reported = archived.get('outputs', {}).get('64', {})
            outputs = [item for kind in ('videos', 'images', 'gifs') for item in reported.get(kind, [])
                       if item.get('type') == 'output' and item.get('filename', '').endswith('.mp4')]
            if len(outputs) == 1:
                native_output = relative_path(root, Path('output') / outputs[0].get('subfolder', '') / outputs[0]['filename'])
        else:
            check('history', 'missing', 'Master Studio')
        output = state.get('output') or {}
        video = artifact('output', 'Master Studio', output, 'path', 'sha256')
        if video and native_output != video.relative_to(root):
            check('history_output', 'changed' if native_output else 'unlinked', 'Master Studio')
        suite = state.get('suite') or {}
        sidecar = artifact('suite_sidecar', 'H3 Project Suite', suite, 'sidecar', 'sidecar_sha256')
        suite_video = artifact('suite_video', 'H3 Project Suite', suite, 'video', 'video_sha256')
        latent = artifact('suite_latent', 'H3 Project Suite', suite, 'latent', 'latent_sha256')
        if suite.get('project'):
            manifest = relative_path(root, SUITE / suite['project'] / 'project.json')
            links = []
            if (root / manifest).is_file():
                links = [entry for clip in read(root / manifest)['clips'] if clip['index'] == suite.get('index')
                         for entry in clip.get('takes', [clip]) if entry['basename'] == suite.get('clip')
                         and entry['take'] == suite.get('take')]
            expected = root / manifest.parent / 'clips' / str(suite.get('clip'))
            sidecar_ok = (sidecar == expected.with_suffix('.json') and suite_video == expected.with_suffix('.mp4')
                          and latent == expected.with_suffix('.safetensors') and frozen is not None
                          and prompt_digest(read(sidecar)['prompt']) == prompt_digest(frozen))
            status = 'verified' if len(links) == 1 and sidecar_ok else 'ambiguous' if len(links) > 1 else 'unlinked'
            check('suite_manifest', status, 'H3 Project Suite', path=str(manifest))
        brain = state.get('brain') or {}
        run = artifact('brain', 'Workflow Monitor Brain', brain, 'run_file')
        if run:
            matching = (read(run)['prompt_id'] == brain.get('run_id') == state.get('prompt_id') == run.parent.name
                        and run.relative_to(root).parent.parent == BRAIN / 'runs')
            check('brain_identity', 'verified' if matching else 'changed', 'Workflow Monitor Brain')
        review = state.get('review') or {}
        if state['status'] == 'approved':
            status = ('verified' if review.get('approved') is True and review.get('sha256') == output.get('sha256')
                      and checks['output']['status'] == 'verified' else 'changed')
        else:
            status = 'awaiting_review' if state['status'] == 'review_pending' else 'recorded' if review else 'unreviewed'
        check('review', status, 'Master Studio')
    except RECORD_ERRORS as error:
        check('record', 'invalid_record', 'Master Studio', detail=str(error))
    return row


def asset_rows(root, projects):
    path = root / DATABASE
    if not path.is_file():
        return {'owner': 'ComfyUI Asset Library', 'status': 'missing', 'path_gaps': []}
    references = defaultdict(set)
    for row in projects:
        for item in row.get('references', []):
            if item.get('loader_path'):
                try:
                    folder, file, _ = production_references.source_path(item['loader_path'], {kind: root / kind for kind in ('input', 'output')})
                    references[str(folder / file)].add(row['path'])
                except ValueError:
                    continue
    gaps, flags = [], Counter()
    try:
        integrity = database_checks(path)
        with open_db(path) as connection:
            aliases = defaultdict(list)
            for asset, content, loader in connection.execute('SELECT id, content_id, loader_path FROM assets'):
                aliases[content].append((asset, loader))
            for content, locator, flagged, digest in connection.execute('SELECT id, path, is_missing, hash FROM asset_contents'):
                available = bool(locator and Path(locator).is_file())
                status = ('missing_flag_with_file' if flagged and available else
                          'flagged_missing' if flagged else 'path_unavailable' if not available else 'present')
                flags[status] += 1
                if status != 'present':
                    gaps.append({'content_id': content, 'path': locator, 'status': status,
                                 'asset_ids': [asset for asset, _ in aliases[content]],
                                 'loader_paths': [loader for _, loader in aliases[content] if loader],
                                 'hash_algorithm': digest.partition(':')[0] if digest else None,
                                 'active_projects': sorted(references.get(locator, ()))})
        return {'owner': 'ComfyUI Asset Library', 'status': 'inspected', 'counts': dict(flags), **integrity,
                'path_gaps': sorted(gaps, key=lambda row: (-len(row['active_projects']), row['content_id']))}
    except RECORD_ERRORS as error:
        return {'owner': 'ComfyUI Asset Library', 'status': 'invalid_record', 'detail': str(error), 'path_gaps': []}


def brain_rows(root):
    raw = {}
    for path in sorted((root / BRAIN / 'runs').glob('*')):
        if path.is_dir() and not path.is_symlink():
            absent = [name for name in FILES if not (path / name).is_file()]
            try:
                run = read(path / 'run.json')
                status = run['status'] if run.get('prompt_id') == path.name else 'identity_mismatch'
            except RECORD_ERRORS:
                status = 'invalid_record'
            raw[path.name] = {'status': status, 'missing_files': absent}
    result = {'owner': 'Workflow Monitor Brain', 'raw_runs': len(raw),
              'absent_streams': {key: row['missing_files'] for key, row in raw.items() if row['missing_files']}}
    try:
        with AnalysisIndex(root / BRAIN / 'analysis') as index:
            stored = {row[0] for row in index.connection.execute('SELECT run_id FROM runs')}
            skipped = index.metadata.get('skipped', [])
            result.update(index_status='present', indexed_runs=len(stored), generation=index.metadata['generation'],
                          index_age_seconds=max(0, round(time.time() - index.metadata['created'])),
                          skipped_at_build=skipped, indexed_runs_missing_raw=sorted(stored - raw.keys()))
    except RECORD_ERRORS as error:
        stored = set()
        result.update(index_status='missing' if isinstance(error, FileNotFoundError) else 'invalid_record', detail=str(error))
    result['eligible_unindexed'] = sorted(key for key, row in raw.items() if key not in stored and row['status'] in TERMINAL)
    return result


def suite_rows(root):
    rows = []
    for path in sorted((root / SUITE).glob('*/project.json')):
        if path.resolve() != path:
            continue
        row = {'path': str(path.relative_to(root)), 'owner': 'H3 Project Suite', 'takes': []}
        try:
            for clip in read(path)['clips']:
                for take in clip.get('takes') or [clip]:
                    name = take['basename']
                    if Path(name).name != name or name in ('', '.', '..'):
                        raise ValueError('Invalid clip basename')
                    status = clip['status'] if clip['basename'] == name else 'alternate'
                    directory = '.trash' if take.get('trashed') else 'clips'
                    base = path.parent / directory / name
                    locators = [relative_path(root, base.with_suffix(ext)) for ext in ('.mp4', '.json', '.safetensors')]
                    row['takes'].append({'status': status, 'index': clip['index'], 'take': take['take'],
                                         'files': [str(p) for p in locators],
                                         'missing': [str(p) for p in locators if not (root / p).is_file()]})
        except RECORD_ERRORS as error:
            row['error'] = str(error)
        rows.append(row)
    return rows


def retention(root, takes, brain, suite):
    approved = set()
    marked = {}
    for row in takes:
        for evidence in row['checks'].values():
            if 'path' in evidence and row.get('status') == 'approved':
                approved.add(evidence['path'])
        run = row['checks'].get('brain', {}).get('path')
        if run and row.get('status') == 'approved':
            approved.update(str(p.relative_to(root)) for p in files((root / run).parent))
        if row.get('status') == 'approved':
            approved.update(str(p.relative_to(root)) for p in files(root / row['path']))
    for project in suite:
        for take in project['takes']:
            if take['status'] == 'approved':
                approved.update([project['path'], *take['files']])
    for directory, label in ((PROJECTS, 'project_records'), (TAKES, 'take_evidence'), (STORY, 'story_job_records'),
                             (SUITE, 'suite_media'), (BRAIN / 'runs', 'raw_telemetry'),
                             (BRAIN / 'analysis', 'derived_analysis'), (Path('output/h3_stages'), 'rebuildable_stage')):
        for path in files(root / directory):
            locator = str(path.relative_to(root))
            marked[locator] = {'path': locator, 'bytes': path.stat().st_size, 'category': label}
    for locator in approved:
        path = root / locator
        if path.is_file():
            marked[locator] = {'path': locator, 'bytes': path.stat().st_size, 'category': 'approved_take_evidence'}
    totals = Counter()
    for item in marked.values():
        totals[item['category']] += item['bytes']
    active_index = str(BRAIN / 'analysis/generations' / (brain.get('generation', '') + '.sqlite'))
    candidates = []
    for item in marked.values():
        path = Path(item['path'])
        old_index = (brain.get('index_status') == 'present' and str(path) != active_index
                     and path.parent == BRAIN / 'analysis/generations' and path.suffix == '.sqlite')
        if old_index:
            candidates.append(dict(item, disposition='review only',
                                   recovery_requires=['raw Brain runs', 'version-matched analyzer'],
                                   recovery_evidence='requires a verified rebuild from the corresponding raw runs'))
        elif item['category'] == 'rebuildable_stage':
            candidates.append(dict(item, disposition='review only',
                                   recovery_requires=['frozen graph', 'referenced inputs and model weights'],
                                   recovery_evidence='stage regeneration has not been tested by this inventory'))
    return {'mode': 'inventory_only', 'bytes_by_category': dict(totals), 'production_cleanup': [],
            'preserve': sorted(approved),
            'protected_analysis': ['active generation and pointer', 'reports and human decision records'],
            'review_candidates': candidates}


def report(root):
    projects = project_rows(root)
    takes = [take_row(root, p.parent, projects) for p in files(root / TAKES) if p.name == 'take.json']
    brain = brain_rows(root)
    suite = suite_rows(root)
    return {'version': 1, 'projects': projects, 'takes': takes, 'assets': asset_rows(root, projects),
            'brain': brain, 'suite': suite, 'retention': retention(root, takes, brain, suite)}


def backup_db(source, destination):
    deadline = time.monotonic() + 5

    def progress(status, remaining, total):
        if status in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) and time.monotonic() > deadline:
            raise TimeoutError('Asset database remained busy during backup')

    with open_db(source) as origin, closing(sqlite3.connect(destination, timeout=5)) as target:
        origin.backup(target, progress=progress)


def rehearse(root, slug, take_locator, destination):
    started = time.monotonic()
    if not slug or Path(slug).name != slug or slug in ('.', '..'):
        raise ValueError('Choose a Storyboard project slug')
    take_locator = relative_path(root, take_locator)
    if not take_locator.is_relative_to(TAKES):
        raise ValueError('Choose a take under user/master_studio/takes')
    destination = destination.absolute()
    if destination.resolve() != destination or any(destination.is_relative_to(root / folder)
            for folder in (PROJECTS, Path('user'), Path('input'), Path('output'))):
        raise ValueError('Choose a new rehearsal directory outside production stores')
    take = take_row(root, root / take_locator, project_rows(root))
    required = ('frozen_inputs', 'history', 'output', 'suite_sidecar', 'suite_video',
                'suite_latent', 'suite_manifest', 'brain_identity', 'review')
    if (take.get('status') != 'approved' or any(take['checks'].get(key, {}).get('status') != 'verified' for key in required)
            or 'history_output' in take['checks']):
        raise ValueError('Selected take does not have complete, verified approved evidence')
    project = root / PROJECTS / slug
    snapshot = production_store.read_project(project)
    references = production_references.bank(snapshot, {kind: root / kind for kind in ('input', 'output')})
    binding = next((r['source'] for r in references['requirements'] if 'source' in r), None)
    if not binding:
        raise ValueError('Select a project with a verified bound reference')
    folder, name, loader = production_references.source_path(binding['loader_path'], {kind: root / kind for kind in ('input', 'output')})
    reference = relative_path(root, folder / name)
    take_files = files(root / take_locator)
    brain_run = root / take['checks']['brain']['path']
    inputs = set(p.relative_to(root) for p in [*files(project), *take_files, *files(brain_run.parent)] if not p.name.endswith('.lock'))
    inputs.add(reference)
    shot = take['checks']['production_shot']
    if shot['status'] == 'linked_by_shot_id':
        production = root / shot['candidates'][0]['path']
        inputs.update(p.relative_to(root) for p in files(production if production.is_dir() else production.parent)
                      if not p.name.endswith('.lock'))
    for key in ('output', 'suite_sidecar', 'suite_video', 'suite_latent', 'suite_manifest'):
        inputs.add(Path(take['checks'][key]['path']))

    destination.mkdir(mode=0o700)
    backup, restore = destination / 'backup', destination / 'restored'
    backup.mkdir()
    restore.mkdir()
    entries = []
    for locator in [*sorted(inputs), DATABASE]:
        locator = relative_path(root, locator)
        stored = backup / locator
        stored.parent.mkdir(parents=True, exist_ok=True)
        if locator == DATABASE:
            backup_db(root / locator, stored)
        else:
            source = root / locator
            expected = file_digest(source)
            shutil.copy2(source, stored)
            if file_digest(stored) != expected or file_digest(source) != expected:
                raise ValueError(f'Source changed during backup: {locator}')
        entries.append({'path': str(locator), 'bytes': stored.stat().st_size,
                        'sha256': file_digest(stored)})
        restored = restore / locator
        restored.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stored, restored)
        if file_digest(restored) != entries[-1]['sha256']:
            raise ValueError(f'Restored file differs: {locator}')

    reopened = production_store.read_project(restore / PROJECTS / slug)
    recovered = take_row(restore, restore / take_locator, project_rows(restore), original=root)
    restored_reference = production_references.inspect_source(loader, {kind: restore / kind for kind in ('input', 'output')})
    index = build_index(restore / BRAIN / 'runs', restore / BRAIN / 'analysis')
    databases = {'assets': database_checks(restore / DATABASE),
                 'brain': database_checks(restore / BRAIN / 'analysis/generations' / (index['generation'] + '.sqlite'))}
    if (reopened['revision'] != snapshot['revision'] or restored_reference['sha256'] != binding['sha256']
            or any(recovered['checks'].get(key, {}).get('status') != 'verified' for key in required)
            or (shot['status'] == 'linked_by_shot_id' and recovered['checks']['production_shot'] != shot)
            or 'history_output' in recovered['checks']
            or any(db['integrity'] != 'ok' or db['foreign_key_violations'] for db in databases.values())):
        raise ValueError('Restored evidence did not match the selected source records')
    output = restore / recovered['checks']['output']['path']
    held = destination / 'omitted-output'
    output.rename(held)
    try:
        incomplete = take_row(restore, restore / take_locator, original=root)
        if incomplete['checks']['output']['status'] != 'missing' or incomplete['checks']['review']['status'] == 'verified':
            raise ValueError('Incomplete restore did not report its missing output')
    finally:
        held.rename(output)
    result = {'version': 1, 'status': 'verified', 'project': slug, 'project_revision': reopened['revision'],
              'take': str(take_locator), 'take_checks': recovered['checks'],
              'reference': {'path': str(reference), 'sha256': binding['sha256']}, 'databases': databases,
              'brain_indexed_runs': index['run_count'], 'negative_check': incomplete['checks']['output'],
              'backup_bytes': sum(entry['bytes'] for entry in entries), 'files': entries,
              'seconds': round(time.monotonic() - started, 2)}
    (destination / 'rehearsal.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('report', help='Inspect the current records without writing to Studio stores')
    restore = commands.add_parser('rehearse', help='Back up and restore selected records in a new directory')
    restore.add_argument('--project', required=True)
    restore.add_argument('--take', required=True)
    restore.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    try:
        result = (report(root) if args.command == 'report' else
                  rehearse(root, args.project, args.take, args.destination))
    except RECORD_ERRORS as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
