import json
from contextlib import closing
from pathlib import Path
import sqlite3
import subprocess
import sys

from studio import production_bootstrap as bootstrap
from studio import production_store as store
from studio.production_validate import SPEC
from storage_audit import backup_db

CLI = Path(__file__).resolve().parents[1] / 'storage_audit.py'


def run_cli(root, *args):
    result = subprocess.run([sys.executable, CLI, '--root', root, *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_inventory_reports_stale_asset_flags_and_keeps_legacy_projects_visible(tmp_path):
    projects = tmp_path / 'studio/projects'
    projects.mkdir(parents=True)
    document = json.loads((SPEC / 'example.production.json').read_text())
    proposal = bootstrap.preview(document, 'demo-film')
    bootstrap.create(projects, proposal, proposal['digest'])
    (projects / 'archive').mkdir()
    (projects / 'archive/production.json').write_text(json.dumps(document))
    path = tmp_path / 'input/photo.png'
    path.parent.mkdir()
    path.write_bytes(b'media')
    database = tmp_path / 'user/comfyui.db'
    database.parent.mkdir()
    with sqlite3.connect(database) as connection:
        connection.executescript('''
            CREATE TABLE asset_contents(id INTEGER, path TEXT, is_missing INTEGER, hash TEXT);
            CREATE TABLE assets(id TEXT, content_id INTEGER, loader_path TEXT);
        ''')
        connection.execute('INSERT INTO asset_contents VALUES(1, ?, 1, ?)', (str(path), 'blake3:example'))
        connection.execute("INSERT INTO assets VALUES('asset-id', 1, 'photo.png')")

    report = run_cli(tmp_path, 'report')
    assert {row['path']: row['status'] for row in report['projects']} == {
        'studio/projects/demo-film': 'current', 'studio/projects/archive': 'legacy_production',
    }
    row = report['assets']['path_gaps'][0]
    assert (row['asset_ids'], row['status'], row['hash_algorithm']) == (['asset-id'], 'missing_flag_with_file', 'blake3')
    assert report['retention']['mode'] == 'inventory_only'
    assert path.read_bytes() == b'media'


def test_report_exposes_current_reference_shots_after_edit(tmp_path):
    projects = tmp_path / 'studio/projects'
    projects.mkdir(parents=True)
    document = json.loads((SPEC / 'example.production.json').read_text())
    proposal = bootstrap.preview(document, 'demo-film')
    bootstrap.create(projects, proposal, proposal['digest'])
    project = projects / 'demo-film'
    creation_snapshot = (project / 'reference-plan.json').read_bytes()
    document['shots'][0]['characters'] = []
    store.commit(project, store.read_project(project)['revision'], {'production': document}, 'Change cast in shot')
    row = run_cli(tmp_path, 'report')['projects'][0]
    assert row['creation_reference_plan'] == 'creation_snapshot_differs'
    assert next(need for need in row['references'] if need['role'] == 'identity')['shots'] == []
    assert (project / 'reference-plan.json').read_bytes() == creation_snapshot


def test_online_backup_includes_committed_wal_pages(tmp_path):
    origin = tmp_path / 'original.sqlite'
    target = tmp_path / 'copy.sqlite'
    with closing(sqlite3.connect(origin)) as source:
        source.execute('PRAGMA journal_mode = WAL')
        source.execute('PRAGMA wal_autocheckpoint = 0')
        source.execute('CREATE TABLE records(value TEXT)')
        source.execute("INSERT INTO records VALUES('committed-in-wal')")
        source.commit()
        assert (tmp_path / 'original.sqlite-wal').stat().st_size > 0
        backup_db(origin, target)
    with closing(sqlite3.connect(target)) as restored:
        assert restored.execute('SELECT value FROM records').fetchone() == ('committed-in-wal',)
