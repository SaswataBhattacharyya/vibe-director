import json
import tempfile
import unittest
from pathlib import Path
from story_builder.services.storage_paths import project_root, media_root, generated_root, project_identity
from story_builder.services.production_story_revisions import write_revision, load_revision
from story_builder.services.media_library import browse_catalogue, name_media_workspace

class NamedProjectStorageTests(unittest.TestCase):
    def test_named_folder_preserves_internal_identity_and_story_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'library').mkdir()
            (root/'library/project-folders.json').write_text(json.dumps({'story-123456789abc':'trial 1 scar'}))
            self.assertEqual(project_root(root,'story-123456789abc'),root/'projects/trial 1 scar')
            self.assertEqual(project_identity(root,'trial 1 scar'),'story-123456789abc')
            self.assertEqual(generated_root(root,'story-123456789abc'),media_root(root,'story-123456789abc')/'generated')
            revision={'revision_id':'story-canon-123456789abc','source_text':'The saved storyboard'}
            run='875d1fc8-bc91-4884-9c1e-71cd1dab6d1d'
            write_revision(root,'story-123456789abc',run,revision)
            self.assertEqual(load_revision(root,'story-123456789abc',run,revision['revision_id']),revision)
            name_media_workspace(root,'story-123456789abc','trial 1 scar')
            result=browse_catalogue(root,'story-123456789abc')
            self.assertEqual(result['workspace_names']['story-123456789abc'],'trial 1 scar')
            self.assertFalse((root/'projects/story-123456789abc').exists())

    def test_registry_rejects_traversal_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'library').mkdir();(root/'projects').mkdir()
            registry=root/'library/project-folders.json'
            registry.write_text(json.dumps({'story-123456789abc':'../escape'}))
            with self.assertRaises(ValueError):project_root(root,'story-123456789abc')
            registry.write_text(json.dumps({'story-123456789abc':'trial 1 scar'}))
            (root/'projects/trial 1 scar').symlink_to(root/'library',target_is_directory=True)
            with self.assertRaises(ValueError):project_root(root,'story-123456789abc')

    def test_deleted_workspace_cannot_be_recreated_by_a_stale_browser(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'library').mkdir()
            (root/'library/deleted-projects.json').write_text('["old-project"]')
            with self.assertRaises(ValueError):media_root(root,'old-project')
            self.assertFalse((root/'projects/old-project').exists())
