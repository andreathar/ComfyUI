"""Preview and publish a draft Studio project from a validated production document."""

import argparse
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from . import production_validate


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def reference_requirements(production):
    shots = production['shots']
    roles = (
        ('locations', 'location', lambda e, s: s['location'] == e),
        ('characters', 'identity', lambda e, s: e in s['characters']),
        ('props', 'prop', lambda e, s: e in s.get('props', [])),
        ('motions', 'motion', lambda e, s: e == s.get('motion')),
    )
    rows = [{'entity': entity['id'], 'role': role, 'status': 'missing',
             'shots': [sh['id'] for sh in shots if uses(entity['id'], sh)]}
            for bank, role, uses in roles for entity in production.get(bank, [])]
    for scene in production['scenes']:
        for character, wardrobe in scene.get('wardrobe', {}).items():
            row = next((r for r in rows if r['role'] == 'wardrobe' and
                        (r['entity'], r['wardrobe']) == (character, wardrobe)), None)
            if row is None:
                row = {'entity': character, 'role': 'wardrobe', 'wardrobe': wardrobe,
                       'status': 'missing', 'shots': []}
                rows.append(row)
            row['shots'].extend(sh['id'] for sh in shots if sh['scene'] == scene['id'] and character in sh['characters'])
    for voice in production.get('voices', []):
        speakers = {c['id'] for c in production['characters'] if c.get('voice') == voice['id']}
        rows.append({'entity': voice['id'], 'role': 'voice', 'status': 'missing',
                     'shots': [sh['id'] for sh in shots if any(d['character'] in speakers for d in sh.get('dialogue', []))]})
    return rows


def preview(document, slug):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or len(slug) > 64:
        raise ValueError('Invalid project slug')
    problems = production_validate.check(document)
    if problems:
        raise ValueError('\n'.join(problems))
    production = json.loads(json_bytes(document))
    rows = reference_requirements(production)
    proposal = {'version': 1, 'status': 'preview_ready', 'slug': slug, 'production': production,
                'reference_plan': rows, 'render_ready': False}
    proposal['digest'] = hashlib.sha256(json_bytes(proposal)).hexdigest()
    return proposal


def publish(stage, destination):
    # Linux renameat2 with RENAME_NOREPLACE also rejects an empty destination.
    rename = ctypes.CDLL(None, use_errno=True).renameat2
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    if rename(-100, os.fsencode(stage), -100, os.fsencode(destination), 1) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination)


def create(projects, proposal, approved_digest):
    expected = preview(proposal['production'], proposal['slug'])
    if expected != proposal or expected['digest'] != approved_digest:
        raise ValueError('Proposal differs from the approved digest')
    projects = Path(projects).absolute()
    if projects.resolve(strict=True) != projects or not projects.is_dir():
        raise ValueError('Projects root must be a real directory without symlinks')
    production = expected['production']
    project = production['project']
    source = project['source_text'].encode()
    destination = projects / expected['slug']
    manifest = {'version': 1, 'slug': expected['slug'], 'code': project['code'], 'title': project['title'],
                'schema_version': production['schema_version'], 'source_sha256': hashlib.sha256(source).hexdigest(),
                'proposal_digest': approved_digest, 'source': 'story/script-v001.md', 'production': 'production.json',
                'reference_plan': 'reference-plan.json', 'assets': 'assets.json', 'bindings': 'bindings.json',
                'transitions': 'shot_transitions.json'}
    immutable = {'project.json': json_bytes(manifest), 'production.json': json_bytes(production), manifest['source']: source}
    files = {**immutable, 'reference-plan.json': json_bytes(expected['reference_plan']),
             'assets.json': json_bytes({}), 'bindings.json': json_bytes({}),
             'shot_transitions.json': json_bytes({sh['id']: 'cut' for sh in production['shots']})}

    def matches(path, entries):
        return all((path / name).resolve() == path / name and (path / name).is_file()
                   and (path / name).read_bytes() == data for name, data in entries.items())

    fd = os.open(projects, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if destination.exists() or destination.is_symlink():
            if not destination.is_symlink() and matches(destination, immutable):
                return {'status': 'already_created', 'manifest': str(destination / 'project.json')}
            raise FileExistsError(errno.EEXIST, 'Project destination already exists', destination)
        for sibling in sorted(projects.iterdir()):
            doc = sibling / 'production.json'
            if not sibling.is_symlink() and not doc.is_symlink() and doc.is_file():
                if json.loads(doc.read_text()).get('project', {}).get('code') == project['code']:
                    raise ValueError(f"Duplicate project code {project['code']} in {sibling.name}")
        with tempfile.TemporaryDirectory(prefix='.bootstrap-', dir=projects) as staging:
            stage = Path(staging) / 'project'
            (stage / 'story').mkdir(parents=True)
            for name, data in files.items():
                (stage / name).write_bytes(data)
            publish(stage, destination)
        if not matches(destination, files):
            raise RuntimeError('Published scaffold did not match the proposal')
    finally:
        os.close(fd)
    return {'status': 'scaffold_created', 'manifest': str(destination / 'project.json')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    review = commands.add_parser('preview')
    review.add_argument('production', type=Path)
    review.add_argument('--slug', required=True)
    apply = commands.add_parser('create')
    apply.add_argument('proposal', type=Path)
    apply.add_argument('--projects', type=Path, required=True)
    apply.add_argument('--approved-digest', required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'preview':
            result = preview(json.loads(args.production.read_text()), args.slug)
        else:
            result = create(args.projects, json.loads(args.proposal.read_text()), args.approved_digest)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print(json_bytes(result).decode(), end='')


if __name__ == '__main__':
    main()
