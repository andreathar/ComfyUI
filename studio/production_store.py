"""Read Studio projects and save canonical shot edits without overwriting newer work."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

from . import production_validate
from .production_bootstrap import json_bytes

REFERENCE_BANK = '_storyboard_references_v1'


class RevisionConflict(ValueError):
    pass


def project_path(project_root):
    root = Path(project_root).absolute()
    if root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError('Project path must be a real directory without symlinks')
    return root


def contained(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Invalid project file path')
    path = root / name
    if path.resolve() != path:
        raise ValueError('Project file path contains a symlink')
    return path


def read_bytes(root, name):
    path = contained(root, name)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        return stream.read()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_project(project_root):
    root = project_path(project_root)
    manifest = json.loads(read_bytes(root, 'project.json'))
    state = {'manifest': manifest}
    for key, default in (('production', 'production.json'), ('assets', 'assets.json'),
                         ('bindings', 'bindings.json'), ('transitions', 'shot_transitions.json')):
        name = manifest.get(key, default)
        if name != default:
            raise ValueError(f'Unsupported project {key} path')
        state[key] = json.loads(read_bytes(root, name))
    problems = production_validate.check(state['production'])
    if problems:
        raise ValueError('\n'.join(problems))
    project = state['production']['project']
    source = read_bytes(root, manifest['source'])
    if (manifest['code'] != project['code'] or source != project['source_text'].encode()
            or hashlib.sha256(source).hexdigest() != manifest['source_sha256']):
        raise ValueError('Project identity or authorized story does not match its manifest')
    state['revision'] = hashlib.sha256(json_bytes(state)).hexdigest()
    return state


def commit(project_root, expected_revision, changes, reason):
    """Save one owned document; asset edits are confined to the storyboard reference bank."""
    if not isinstance(changes, dict) or set(changes) not in ({'production'}, {'assets'}):
        raise ValueError('Save one canonical document at a time')
    key = next(iter(changes))
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('A save reason is required')
    root = project_path(project_root)
    lock_path = contained(root, '.production.lock')
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        before = read_project(root)
        if before['revision'] != expected_revision:
            raise RevisionConflict('The project changed; reload it before saving')
        document = json.loads(json_bytes(changes[key]))
        if key == 'production':
            problems = production_validate.check(document)
            if problems:
                raise ValueError('\n'.join(problems))
            original = before['production']['project']
            if any(document['project'][field] != original[field] for field in ('code', 'source_text')):
                raise ValueError('Story replacement and project identity require a separate reviewed change')
        elif (not isinstance(document, dict) or REFERENCE_BANK not in document
              or {k: v for k, v in document.items() if k != REFERENCE_BANK}
              != {k: v for k, v in before['assets'].items() if k != REFERENCE_BANK}):
            raise ValueError('Existing assets must stay intact; edit only the storyboard reference bank')
        if document == before[key]:
            return before
        history = contained(root, 'revisions')
        history.mkdir(exist_ok=True)
        previous = contained(root, f'revisions/{before["revision"]}.json')
        if previous.exists():
            recorded = json.loads(read_bytes(root, f'revisions/{before["revision"]}.json'))
            if any(recorded.get(key) != value for key, value in before.items()):
                raise ValueError('Existing revision history differs from this project')
        else:
            history_fd, history_tmp = tempfile.mkstemp(prefix='.revision-', dir=history)
            try:
                with os.fdopen(history_fd, 'wb') as stream:
                    stream.write(json_bytes({**before, 'reason': reason.strip()}))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.link(history_tmp, previous)
            finally:
                os.unlink(history_tmp)
        sync_directory(history)
        sync_directory(root)
        temporary_fd, temporary = tempfile.mkstemp(prefix='.production-', dir=root)
        try:
            with os.fdopen(temporary_fd, 'wb') as stream:
                stream.write(json_bytes(document))
                stream.flush()
                os.fsync(stream.fileno())
            # Recheck independent asset/binding writers before publishing the edit.
            if read_project(root)['revision'] != expected_revision:
                raise RevisionConflict('The project changed while saving')
            os.replace(temporary, contained(root, key + '.json'))
            sync_directory(root)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return read_project(root)
    finally:
        os.close(fd)
