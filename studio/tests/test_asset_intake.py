import io
import stat

import pytest
from PIL import Image, PngImagePlugin

from studio import asset_intake as intake


def still(path, color='red'):
    info = PngImagePlugin.PngInfo()
    info.add_text('workflow', '{"fixture":true}')
    Image.new('RGB', (80, 60), color).save(path, pnginfo=info)


@pytest.fixture
def workspace(tmp_path):
    inbox = tmp_path / 'inbox'
    inbox.mkdir()
    (tmp_path / 'input').mkdir()
    still(inbox / 'source.png')
    return tmp_path, inbox


def test_inventory_is_read_only_and_skips_links_duplicates_and_nonstills(workspace):
    root, inbox = workspace
    (inbox / 'z.png').write_bytes((inbox / 'source.png').read_bytes())
    (inbox / 'broken.png').write_bytes(b'invalid image')
    (inbox / 'clip.mp4').write_bytes(b'not an image')
    (inbox / 'link.png').symlink_to(inbox / 'source.png')
    report = intake.scan(inbox)
    assert not (root / 'input/refs').exists()
    assert {x['source']: x['status'] for x in report} == {'broken.png': 'unreadable', 'link.png': 'symlink', 'source.png': 'ready', 'z.png': 'duplicate'}


def test_plan_and_copy_preserves_metadata_and_is_idempotent(workspace):
    root, inbox = workspace
    plan = make_plan(inbox)
    item, = plan['items']
    assert item['destination'].startswith('input/refs/film/prop-lamp-')
    assert not (root / item['destination']).exists()
    receipt = intake.apply(root, inbox, plan, plan['id'], [item['id']])
    assert receipt[0]['status'] == 'copied'
    assert (root / item['destination']).read_bytes() == (inbox / 'source.png').read_bytes()
    assert intake.apply(root, inbox, plan, plan['id'], [item['id']])[0]['status'] == 'already_present'


def make_plan(inbox):
    rows = intake.scan(inbox)
    row = next(x for x in rows if x['source'] == 'source.png')
    return intake.plan('film', rows, {row['id']: {'role': 'prop', 'slug': 'lamp'}})


def test_stale_approval_and_changed_source_do_not_copy(workspace):
    root, inbox = workspace
    plan = make_plan(inbox)
    item, = plan['items']
    with pytest.raises(ValueError, match='approval'):
        intake.apply(root, inbox, plan, 'wrong', [item['id']])
    still(inbox / 'source.png', 'blue')
    assert intake.apply(root, inbox, plan, plan['id'], [item['id']])[0]['status'] == 'blocked'
    assert not (root / item['destination']).exists()


def test_destination_symlink_and_collision_are_not_overwritten(workspace):
    root, inbox = workspace
    plan = make_plan(inbox)
    item, = plan['items']
    dest = root / item['destination']
    dest.parent.mkdir(parents=True)
    foreign = root / 'foreign.png'
    foreign.write_bytes(b'foreign')
    dest.symlink_to(foreign)
    assert intake.apply(root, inbox, plan, plan['id'], [item['id']])[0]['status'] == 'blocked'
    assert foreign.read_bytes() == b'foreign'
    dest.unlink()
    dest.write_bytes(b'occupied')
    assert intake.apply(root, inbox, plan, plan['id'], [item['id']])[0]['status'] == 'blocked'
    assert dest.read_bytes() == b'occupied'


def test_published_copy_with_directory_sync_error_is_not_reported_as_blocked(workspace, monkeypatch):
    root, inbox = workspace
    document = make_plan(inbox)
    item, = document['items']
    original_sync = intake.os.fsync

    def sync(fd):
        if stat.S_ISDIR(intake.os.fstat(fd).st_mode):
            raise OSError('directory sync failed')
        original_sync(fd)

    monkeypatch.setattr(intake.os, 'fsync', sync)
    receipt, = intake.apply(root, inbox, document, document['id'], [item['id']])
    assert receipt['status'] == 'published_unverified'
    assert (root / item['destination']).read_bytes() == (inbox / item['source']).read_bytes()


def test_review_assignments_cannot_escape_project_or_select_unknown_rows(workspace):
    _, inbox = workspace
    rows = intake.scan(inbox)
    with pytest.raises(ValueError):
        intake.plan('../outside', rows, {})
    with pytest.raises(ValueError):
        intake.plan('film', rows, {'unknown': {'role': 'prop', 'slug': 'lamp'}})
    with pytest.raises(ValueError):
        intake.plan('film', rows, {rows[0]['id']: {'role': 'prop', 'slug': '../escape'}})


def test_preview_shows_selected_thumbnail_and_escapes_filename(workspace):
    _, inbox = workspace
    (inbox / 'source.png').rename(inbox / '<label>.png')
    row, = intake.scan(inbox)
    document = intake.plan('film', [row], {row['id']: {'role': 'prop', 'slug': 'lamp'}})
    html = intake.preview(inbox, document)
    assert '&lt;label&gt;.png' in html and '<label>' not in html
    assert 'data:image/png;base64,' in html
    assert document['id'] in html


def test_thumbnail_contains_pixels_but_no_metadata(workspace):
    _, inbox = workspace
    row, = intake.scan(inbox)
    with Image.open(io.BytesIO(intake.thumbnail(inbox, row))) as image:
        assert image.getpixel((3, 3)) == (255, 0, 0)
        assert image.info == {}
