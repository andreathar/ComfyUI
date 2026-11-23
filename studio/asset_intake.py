"""Read-only reference intake and explicitly approved, no-clobber copies."""

import argparse
import base64
from contextlib import contextmanager
import hashlib
from html import escape
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from PIL import Image, ImageOps

FORMATS = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG', '.webp': 'WEBP'}
ROLES = ('identity', 'wardrobe', 'environment', 'prop', 'composed-frame', 'other')
DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
MAX_BYTES = 24 << 20
MAX_PIXELS = 25_000_000
MAX_ENTRIES = 512
WORKSPACE = Path(__file__).resolve().parents[1]


@contextmanager
def directory(path, *, create=False):
    path = Path(os.path.abspath(path))
    fd = os.open(path.anchor, DIRECTORY)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, dir_fd=fd)
                except FileExistsError:
                    pass
            child = os.open(part, DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def read_stable(fd, name):
    if not isinstance(name, str) or name in ('', '.', '..') or '/' in name or '\0' in name:
        raise ValueError('Invalid inbox filename')
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    with os.fdopen(handle, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise ValueError('Not a bounded regular file')
        data = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
        current = os.stat(name, dir_fd=fd, follow_symlinks=False)
        snapshot = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(data) != before.st_size or snapshot(before) != snapshot(after) or snapshot(after) != snapshot(current):
            raise ValueError('Source changed during read')
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect_image(data, suffix):
    image = Image.open(io.BytesIO(data))
    try:
        if image.format != FORMATS[suffix] or image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Unexpected format, size or frame count')
        image.load()
        return ImageOps.exif_transpose(image)
    finally:
        image.close()


def scan(inbox):
    rows, seen = [], set()
    with directory(inbox) as fd:
        with os.scandir(fd) as entries:
            names = []
            for entry in entries:
                if len(names) == MAX_ENTRIES:
                    raise ValueError(f'Inbox exceeds {MAX_ENTRIES} entries; choose a smaller batch')
                names.append(entry.name)
        for name in sorted(names):
            suffix = Path(name).suffix.lower()
            if suffix not in FORMATS:
                continue
            row = {'id': digest(os.fsencode(name))[:20], 'source': name, 'status': 'unreadable'}
            rows.append(row)
            try:
                mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
                if stat.S_ISLNK(mode):
                    row['status'] = 'symlink'
                    continue
                data = read_stable(fd, name)
                with inspect_image(data, suffix) as image:
                    row.update(width=image.width, height=image.height, bytes=len(data), sha256=digest(data))
            except (OSError, ValueError, Image.DecompressionBombError):
                continue
            row['status'] = 'duplicate' if row['sha256'] in seen else 'ready'
            seen.add(row['sha256'])
    return rows


def thumbnail(inbox, item):
    data = source_bytes(inbox, item)
    with inspect_image(data, Path(item['source']).suffix.lower()) as image:
        image.thumbnail((480, 480))
        # Create fresh pixels; don't send workflow text, EXIF or the source basename.
        with Image.new('RGB', image.size, '#eeeeee') as clean, image.convert('RGBA') as rgba:
            clean.paste(rgba, mask=rgba.getchannel('A'))
            output = io.BytesIO()
            clean.save(output, format='PNG')
            return output.getvalue()


def source_bytes(inbox, item):
    with directory(inbox) as fd:
        data = read_stable(fd, item['source'])
    if digest(data) != item['sha256']:
        raise ValueError('Source bytes changed since review')
    return data


def slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value) or len(value) > 48:
        raise ValueError('Expected a lowercase slug of at most 48 characters')
    return value


def destination(project, item):
    suffix = Path(item['source']).suffix.lower()
    h = item['sha256']
    if item['role'] not in ROLES or suffix not in FORMATS or not isinstance(h, str) or not re.fullmatch(r'[a-f0-9]{64}', h):
        raise ValueError('Invalid reference role, format or digest')
    return f"input/refs/{slug(project)}/{item['role']}-{slug(item['slug'])}-{h[:16]}{suffix}"


def document_id(document):
    return digest(json.dumps(document, sort_keys=True, separators=(',', ':')).encode())


def plan(project, rows, assignments):
    items = []
    by_id = {row['id']: row for row in rows if row['status'] in ('ready', 'duplicate')}
    for asset_id, assignment in sorted(assignments.items()):
        if asset_id not in by_id or not isinstance(assignment, dict) or set(assignment) != {'role', 'slug'}:
            raise ValueError(f'Invalid review assignment for {asset_id}')
        row = by_id[asset_id]
        item = {key: row[key] for key in ('id', 'source', 'sha256')}
        item.update(assignment)
        item['destination'] = destination(project, item)
        items.append(item)
    if len({item['destination'] for item in items}) != len(items):
        raise ValueError('Multiple items map to the same destination')
    body = {'version': 1, 'project': slug(project), 'items': items}
    return {**body, 'id': document_id(body)}


class PublishedCopyError(OSError):
    """A destination was published, but a later verification step failed."""


def copy_verified(fd, name, data, sha256):
    temporary = f'.intake-{uuid.uuid4().hex}.tmp'
    published = False
    try:
        with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=fd), 'wb') as stream:
            try:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                try:
                    os.link(temporary, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                    published = True
                except FileExistsError:
                    pass
                if digest(read_stable(fd, name)) != sha256:
                    raise ValueError('Destination has different bytes')
            finally:
                os.unlink(temporary, dir_fd=fd)
        os.fsync(fd)
    except (OSError, ValueError) as exc:
        if published:
            raise PublishedCopyError(str(exc)) from exc
        raise
    return 'copied' if published else 'already_present'


def preview(inbox, document):
    result = ['<!doctype html><html lang="en"><meta charset="utf-8">',
              '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:">',
              '<title>Reference intake review</title><h1>Reference intake review</h1>',
              f"<p>Plan digest: <code>{escape(document['id'])}</code></p>"]
    for item in document['items']:
        pixels = base64.b64encode(thumbnail(inbox, item)).decode('ascii')
        result.extend((f'<figure><img src="data:image/png;base64,{pixels}" alt="Proposed reference">',
                       f"<figcaption><code>{escape(item['id'])}</code>: {escape(item['source'])} "
                       f"&rarr; {escape(item['destination'])}</figcaption></figure>"))
    return '\n'.join([*result, '</html>'])


def apply(workspace, inbox, document, approved_id, selected):
    body = {key: value for key, value in document.items() if key != 'id'}
    if document.get('id') != approved_id or document_id(body) != approved_id or body.get('version') != 1:
        raise ValueError('Invalid plan or approval digest')
    items = {item['id']: item for item in body['items']}
    if not selected or len(set(selected)) != len(selected) or any(asset_id not in items for asset_id in selected):
        raise ValueError('Select distinct asset IDs listed in the approved plan')
    project = slug(body['project'])
    for item in items.values():
        if item['destination'] != destination(project, item):
            raise ValueError('Destination disagrees with the reviewed naming policy')
    dest_dir = Path(workspace) / 'input' / 'refs' / project
    receipts = []
    for asset_id in selected:
        item = items[asset_id]
        receipt = {'id': asset_id, 'plan_id': approved_id, 'destination': item['destination'], 'sha256': item['sha256']}
        try:
            data = source_bytes(inbox, item)
            with inspect_image(data, Path(item['source']).suffix.lower()):
                pass
            with directory(dest_dir, create=True) as fd:
                receipt['status'] = copy_verified(fd, Path(item['destination']).name, data, item['sha256'])
        except PublishedCopyError as exc:
            receipt.update(status='published_unverified', reason=str(exc))
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            receipt.update(status='blocked', reason=str(exc))
        receipts.append(receipt)
    return receipts


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    scan_cmd = subs.add_parser('scan')
    scan_cmd.add_argument('inbox', type=Path)
    plan_cmd = subs.add_parser('plan')
    plan_cmd.add_argument('project')
    plan_cmd.add_argument('inventory')
    plan_cmd.add_argument('assignments')
    preview_cmd = subs.add_parser('preview')
    preview_cmd.add_argument('inbox', type=Path)
    preview_cmd.add_argument('plan')
    apply_cmd = subs.add_parser('apply')
    apply_cmd.add_argument('inbox', type=Path)
    apply_cmd.add_argument('plan')
    apply_cmd.add_argument('--approve', required=True)
    apply_cmd.add_argument('--select', nargs='+', required=True)
    args = parser.parse_args()
    blocked = False
    try:
        if args.command == 'scan':
            result = scan(args.inbox)
        elif args.command == 'plan':
            result = plan(args.project, load(args.inventory), load(args.assignments))
        elif args.command == 'preview':
            print(preview(args.inbox, load(args.plan)))
            return 0
        else:
            receipts = apply(WORKSPACE, args.inbox, load(args.plan), args.approve, args.select)
            blocked = any(row['status'] not in ('copied', 'already_present') for row in receipts)
            result = receipts
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f'{exc}\n')
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return int(blocked)


if __name__ == '__main__':
    sys.exit(main())
