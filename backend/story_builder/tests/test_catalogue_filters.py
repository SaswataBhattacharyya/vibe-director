"""CPU metadata filtering; only disposable project manifests are written."""
import unittest
from pathlib import Path
from story_builder.services import media_library as media
from story_builder.services.catalogue_filters import CatalogueFilters, content_indexed
from story_builder.tests import test_media_library as fixtures


class CatalogueFilterTests(unittest.TestCase):
    def setUp(self):
        fixtures.MediaLibraryTests.setUp(self)
        self.addCleanup(self.verify_cleanup)

    def verify_cleanup(self):
        self.temporary.cleanup()
        self.assertFalse(Path(self.temporary.name).exists())

    def test_index_filter_name_sort_and_paging_use_full_result_set(self):
        rows = [media.register_upload(self.root, 'filters', filename=name,
            content=fixtures.MediaLibraryTests.png(self, color), role='character_master')
            for name, color in [('Zulu.png', (255,0,0)), ('alpha.png', (0,255,0)), ('Beta.png', (0,0,255))]]
        media.save_semantic_content_index(self.root, 'filters', rows[1]['asset_id'],
            source_sha256=rows[1]['sha256'], modality='image', model='facebook/pe-av-base', vector=[1.0, 0.0])
        options = dict(source='current', kinds='image', order='name_asc', limit=1)
        first = media.browse_catalogue(self.root, 'filters', **options)
        second = media.browse_catalogue(self.root, 'filters', **options, offset=1)
        self.assertEqual(first['total'], 3)
        self.assertEqual([first['assets'][0]['filename'], second['assets'][0]['filename']], ['alpha.png','Beta.png'])
        indexed = media.browse_catalogue(self.root, 'filters', **options, content_index='indexed')
        self.assertEqual(indexed['total'], 1)
        self.assertTrue(indexed['assets'][0]['content_indexed'])
        self.assertNotIn('vector', indexed['assets'][0]['semantic_content_index'])
        self.assertEqual(media.browse_catalogue(self.root, 'filters', **options, content_index='unindexed')['total'], 2)
        self.assertEqual(media.browse_catalogue(self.root, 'filters', **options, role='style_reference')['total'], 0)

    def test_audio_dates_and_stale_index_metadata_are_truthful(self):
        row = {'kind':'audio','audio_category':'voice','roles':['project_audio'],
               'created_at':'2026-11-06T10:00:00Z','sha256':'a'*64,
               'metadata':{'analyzer_run_id':'saved-run'}}
        filters = CatalogueFilters(audio_category='voice', role='project_audio',
            created_after='2026-11-06', created_before='2026-11-06')
        self.assertTrue(filters.matches(row))
        self.assertFalse(filters.matches({**row,'kind':'video'}))
        self.assertFalse(filters.matches({**row,'created_at':'2026-11-05T23:59:59Z'}))
        self.assertFalse(filters.matches({**row,'created_at':''}))
        self.assertFalse(content_indexed(row))
        row['semantic_content_index'] = {'model':'model','dimension':2,'source_sha256':'b'*64}
        self.assertFalse(content_indexed(row))
        row['semantic_content_index']['source_sha256'] = row['sha256']
        self.assertTrue(content_indexed(row))
        for options in ({'content_index':'analyzed'}, {'audio_category':'speech'},
                        {'created_after':'invalid'}, {'created_after':'2026-11-07','created_before':'2026-11-06'}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                CatalogueFilters(**options)

    def test_literal_search_preserves_analysis_summary_before_pagination(self):
        media.register_upload(self.root, 'filters', filename='ordinary.png',
            content=fixtures.MediaLibraryTests.png(self, (255, 0, 0)), role='project_image')
        match = media.register_upload(self.root, 'filters', filename='another.png',
            content=fixtures.MediaLibraryTests.png(self, (0, 255, 0)), role='project_image',
            metadata={'analysis_summary': 'A luminous jellyfish in the ocean.'})
        result = media.browse_catalogue(self.root, 'filters', source='current', query='JELLYFISH', limit=1)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['assets'][0]['asset_id'], match['asset_id'])
