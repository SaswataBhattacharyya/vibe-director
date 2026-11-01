import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / 'tools/migrate_local_layout.py'
spec = importlib.util.spec_from_file_location('layout_migration', SCRIPT)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class LocalLayoutMigrationTests(unittest.TestCase):
    def fixture(self, root):
        data = root / 'local_data'
        generated = data / 'assets/ws'
        generated.mkdir(parents=True)
        (generated / 'clip.mp4').write_bytes(b'preserved media')
        manifest = data / 'media-projects/ws/production'
        manifest.mkdir(parents=True)
        original = {'assets': [{'relative_path': 'inputs/media/audio/file.mp3'}]}
        (manifest / 'assets.json').write_text(json.dumps(original))
        downloads = data / 'donor_migration/video_repertoire/downloads'
        downloads.mkdir(parents=True)
        (downloads / 'download.mp4').write_bytes(b'download')
        dbdir = data / 'storage/production'
        dbdir.mkdir(parents=True)
        with sqlite3.connect(dbdir / 'ledger.sqlite3') as db:
            db.execute('create table jobs(status text, metadata text)')
            db.execute('insert into jobs values (?,?)', ('completed', json.dumps({'path': str(generated / 'clip.mp4')})))
        return data, original

    def test_move_rewrite_and_rollback_preserve_bytes_and_inode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data, original = self.fixture(root)
            inode = (data / 'assets/ws/clip.mp4').stat().st_ino
            migration.migrate(root, True)
            self.assertEqual((data / 'projects/ws/media/generated/clip.mp4').stat().st_ino, inode)
            manifest = data / 'projects/ws/media/assets.json'
            self.assertEqual(json.loads(manifest.read_text())['assets'][0]['relative_path'], 'imports/audio/file.mp3')
            with sqlite3.connect(data / 'services/production/ledger.sqlite3') as db:
                self.assertEqual(json.loads(db.execute('select metadata from jobs').fetchone()[0])['path'], str(data / 'projects/ws/media/generated/clip.mp4'))
            migration.rollback(root)
            self.assertEqual((data / 'assets/ws/clip.mp4').stat().st_ino, inode)
            self.assertEqual(json.loads((data / 'media-projects/ws/production/assets.json').read_text()), original)
            self.assertEqual((data / 'donor_migration/video_repertoire/downloads/download.mp4').read_bytes(), b'download')

    def test_collision_and_active_queue_rejected_before_moves(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data, _ = self.fixture(root)
            target = data / 'projects/ws/media/generated'
            target.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'occupied'):
                migration.migrate(root, True)
            target.rmdir()
            with sqlite3.connect(data / 'storage/production/ledger.sqlite3') as db:
                db.execute("update jobs set status='running'")
            with self.assertRaisesRegex(ValueError, 'Active jobs'):
                migration.migrate(root, True)
            self.assertTrue((data / 'assets/ws/clip.mp4').exists())
