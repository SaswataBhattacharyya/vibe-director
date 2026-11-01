"""Producer/consumer and rollback coverage for the real offline migration."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from story_builder.services import media_library as library
from story_builder.services.storage_paths import shared_file, load_project_documents

spec = importlib.util.spec_from_file_location('storage_migration', Path(__file__).resolve().parents[3] / 'tools/migrate_shared_media.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)

class StorageMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'data'; self.root.mkdir()
    def put(self, relative, content):
        p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content);return p
    def fixture(self):
        content=b'original-media'; sha=hashlib.sha256(content).hexdigest()
        self.put('library/downloads/youtube/movie.mp4', content)
        self.put('services/media/analyses/video_audio_analyzer/run-a/frames/a.png',content)
        self.put('projects/source/media/generated/analysis/legacy/a.png',content)
        common={'workspace_id':'source','sha256':sha,'size_bytes':len(content),'created_at':'2026-01-01','roles':[],'media':{},'metadata':{}}
        rows=[{**common,'asset_id':'pa-1111111111111111','kind':'video','source':'youtube_download','relative_path':'movie.mp4','filename':'movie.mp4','media_type':'video/mp4'},
              {**common,'asset_id':'pa-2222222222222222','kind':'image','source':'project_output','relative_path':'analysis/legacy/a.png','filename':'a.png','media_type':'image/png','metadata':{'analyzer_run_id':'run-a'}}]
        manifest=self.put('projects/source/media/assets.json',json.dumps({'schema_version':1,'assets':rows}).encode())
        self.put('services/music/runs/job-a/full.ckpt',b'checkpoint-protected')
        self.put('services/music/state.json',json.dumps({'projects':[{'id':'ace-a','workspace_id':'source','adapters':[]}]}).encode())
        return manifest, manifest.read_bytes()
    def test_shared_only_occurrences_are_visible_without_project_manifest(self):
        self.fixture()
        with patch.object(migration, 'assert_idle'):
            migration.apply(self.root, migration.inventory(self.root), Path(self.temp.name)/'journal')
        path=self.root/'video_repertoire/catalog.json'
        data=json.loads(path.read_text())
        for row in data['assets']:
            row['workspace_id']='tool-library'
        path.write_text(json.dumps(data))
        result=library.list_assets(self.root,'tool-library',kind='image')
        self.assertEqual(result['total'],1)
        asset=result['assets'][0]
        self.assertIn('/tool-library/',asset['content_url'])
        self.assertTrue(library.asset_path(self.root,'tool-library',asset['asset_id'])[0].is_file())
        self.assertEqual(library.list_assets(self.root,'unrelated',kind='image')['total'],0)

    def test_shared_only_mutations_and_checked_deletion(self):
        manifest,_ = self.fixture()
        with patch.object(migration, 'assert_idle'):
            migration.apply(self.root, migration.inventory(self.root), Path(self.temp.name)/'journal')
        manifest.unlink()  # exactly the shared-only state left by project pruning
        identity='pa-2222222222222222'
        library.update_annotations(self.root,'source',identity,description='reviewed frame',tags=['scene'])
        library.assign_role(self.root,'source',identity,'project_image')
        library.save_image_analysis(self.root,'source',identity,job_id='abcde123456789ab',mode='quick',source_sha256=hashlib.sha256(b'original-media').hexdigest(),analysis={'summary':'A scene'},description='reviewed frame',tags=['scene'])
        row=library.list_assets(self.root,'source',kind='image')['assets'][0]
        self.assertEqual(row['description'],'reviewed frame')
        self.assertEqual(len(row['metadata']['image_analyses']),1)
        with self.assertRaises(library.ProductionAssetError):
            library.update_annotations(self.root,'unrelated',identity,description='wrong owner',tags=[])
        path=library.asset_path(self.root,'source',identity)[0]
        preview=library.deletion_preview(self.root,'source',identity)
        self.assertTrue(preview['can_delete'])
        with self.assertRaises(library.ProductionAssetError):
            library.delete_media_file(self.root,'source',identity,'wrong hash')
        self.assertTrue(path.exists())
        saved=self.put('projects/consumer/story/selection.json',json.dumps({'reference':identity}).encode())
        self.assertFalse(library.deletion_preview(self.root,'source',identity)['can_delete'])
        with self.assertRaises(library.ProductionAssetError):
            library.delete_media_file(self.root,'source',identity,preview['sha256'])
        saved.unlink()
        library.delete_media_file(self.root,'source',identity,preview['sha256'])
        self.assertFalse(path.exists())
        self.assertEqual(library.list_assets(self.root,'source',kind='image')['total'],0)
        self.assertTrue(library.asset_path(self.root,'source','pa-1111111111111111')[0].exists())

    def test_apply_resolves_original_ids_links_without_copy_and_rollback_restores_bytes(self):
        manifest,before=self.fixture();report=migration.inventory(self.root)
        self.assertEqual(len(report['publications']),1) # recovers legacy mapping by verified content
        journal=Path(self.temp.name)/'journal'
        with patch.object(migration,'assert_idle'):
            migration.apply(self.root,report,journal)
        for identity in ('pa-1111111111111111','pa-2222222222222222'):
            self.assertEqual(library.asset_path(self.root,'source',identity)[0].read_bytes(),b'original-media')
        self.assertFalse((self.root/'projects/source/media/generated/analysis/legacy/a.png').exists())
        self.assertEqual(library.browse_catalogue(self.root,'',source='repertoire')['total'],1)
        self.assertEqual(library.browse_catalogue(self.root,'',source='downloaded')['total'],1)
        linked=library.reuse_catalogue_asset(self.root,'target',source_workspace_id='source',asset_id='pa-2222222222222222')
        self.assertEqual(library.asset_path(self.root,'target',linked['asset_id'])[0],library.asset_path(self.root,'source','pa-2222222222222222')[0])
        self.assertFalse((self.root/'projects/target/media/imports').exists())
        library.update_annotations(self.root,'target',linked['asset_id'],description='target only',tags=[] )
        self.assertNotEqual(library.browse_catalogue(self.root,'',source='repertoire')['assets'][0].get('description'),'target only')
        self.assertEqual((self.root/'ace_step/runs/job-a/full.ckpt').read_bytes(),b'checkpoint-protected')
        state=json.loads((self.root/'ace_step/state.json').read_text())
        self.assertEqual(load_project_documents(self.root,state)['projects'][0]['id'],'ace-a')
        again=migration.inventory(self.root)
        self.assertEqual(again['moves'],[]);self.assertEqual(again['publications'],[])
        with patch.object(migration,'assert_idle'):
            migration.rollback(self.root,journal)
        self.assertEqual(manifest.read_bytes(),before)
        self.assertEqual((self.root/'services/music/runs/job-a/full.ckpt').read_bytes(),b'checkpoint-protected')
        self.assertTrue((self.root/'projects/source/media/generated/analysis/legacy/a.png').is_file())
    def test_unresolved_or_changed_publication_blocks_before_move(self):
        self.fixture();self.put('projects/source/media/generated/analysis/legacy/a.png',b'changed')
        with self.assertRaisesRegex(ValueError,'Publication missing/changed'): migration.inventory(self.root)
        self.assertTrue((self.root/'library/downloads/youtube/movie.mp4').exists())
    def test_shared_resolver_rejects_traversal_and_symlinks(self):
        path=self.put('video_repertoire/runs/run-a/a.png',b'good')
        outside=self.put('private.png',b'private')
        (path.parent/'link.png').symlink_to(outside)
        for relative in ('../private.png','runs/run-a/link.png'):
            with self.assertRaises(ValueError): shared_file(self.root,{'store':'repertoire','path':relative})
    def test_structured_job_and_ace_request_paths_move_without_rewriting_logs(self):
        old_download=self.put('library/downloads/youtube/sample.mp4',b'media')
        old_run=self.put('services/music/runs/job-a/checkpoint.bin',b'ckpt')
        job_path=self.put('services/media/jobs/youtube/job-a/job.json',json.dumps({
            'request':{'source_path':str(old_download)},
            'result':{'output_path':str(old_download)},
            'message':f'Historical log mentioned {old_download}',
            'error':f'Historical error mentioned {old_run}',
        }).encode())
        request_path=self.put('services/music/runs/job-a/training_request.json',json.dumps({
            'dataset':{'path':str(self.root/'services/music/datasets/ds-a')},
            'command':['--data',str(self.root/'services/music/datasets/ds-a')],
        }).encode())
        report=migration.inventory(self.root)
        self.assertEqual(len(report['job_updates']),1)
        self.assertEqual(len(report['ace_request_updates']),1)
        journal=Path(self.temp.name)/'path-journal'
        with patch.object(migration,'assert_idle'):
            migration.apply(self.root,report,journal)
        moved_job=json.loads((self.root/'services/media/jobs/youtube/job-a/job.json').read_text())
        self.assertEqual(moved_job['request']['source_path'],str(self.root/'youtube_downloads/files/sample.mp4'))
        self.assertEqual(moved_job['result']['output_path'],str(self.root/'youtube_downloads/files/sample.mp4'))
        self.assertIn('library/downloads/youtube',moved_job['message'])
        moved_request=json.loads((self.root/'ace_step/runs/job-a/training_request.json').read_text())
        self.assertEqual(moved_request['dataset']['path'],str(self.root/'ace_step/datasets/ds-a'))
        self.assertIn('services/music/datasets',moved_request['command'][1])
        with patch.object(migration,'assert_idle'):
            migration.rollback(self.root,journal)
        self.assertEqual(job_path.read_text(),json.dumps({
            'request':{'source_path':str(old_download)},'result':{'output_path':str(old_download)},
            'message':f'Historical log mentioned {old_download}','error':f'Historical error mentioned {old_run}',
        }))
        self.assertTrue(request_path.exists())
    def test_donor_imports_join_download_root_and_manifest_relinks(self):
        content=b'legacy donor download';sha=hashlib.sha256(content).hexdigest()
        media=self.put('engines/youtube-import/out_videos/old clip.mp4',content)
        manifest=self.put('library/catalog/donor-video/manifests/video-old.json',json.dumps({
            'path':str(media),'sha256':sha,
        }).encode())
        report=migration.inventory(self.root)
        self.assertIn({'old':'engines/youtube-import/out_videos',
                       'new':'youtube_downloads/files/legacy_import'},report['moves'])
        self.assertEqual(len(report['manifest_updates']),1)
        journal=Path(self.temp.name)/'donor-journal'
        with patch.object(migration,'assert_idle'):
            migration.apply(self.root,report,journal)
        expected=self.root/'youtube_downloads/files/legacy_import/old clip.mp4'
        moved_manifest=self.root/'video_repertoire/legacy/donor-video/manifests/video-old.json'
        self.assertEqual(json.loads(moved_manifest.read_text())['path'],str(expected))
        self.assertEqual(expected.read_bytes(),content)
        with patch.object(migration,'assert_idle'):
            migration.rollback(self.root,journal)
        self.assertEqual(manifest.read_text(),json.dumps({'path':str(media),'sha256':sha}))
        self.assertEqual(media.read_bytes(),content)
    def test_collision_blocks_without_overwrite(self):
        self.fixture();self.put('youtube_downloads/files/movie.mp4',b'different')
        with self.assertRaisesRegex(ValueError,'Destination collision'): migration.inventory(self.root)
