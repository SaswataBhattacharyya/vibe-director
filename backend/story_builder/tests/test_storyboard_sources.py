"""Standalone outlines and reviewed Backlot edits use disposable project state."""
import json
import uuid
import unittest
from pathlib import Path

from story_builder.tests import test_storyboard as fixtures
from story_builder.services import storyboard_sources, production_board, interface_sessions, projects
from story_builder.services.production_ledger import LedgerConflict


class StoryboardSourceTests(unittest.TestCase):
    def setUp(self):
        fixtures.StoryboardTests.setUp(self)
        projects.activate(self.root, self.w, 'Storyboard test', {})
        self.addCleanup(self.verify_cleanup)

    def verify_cleanup(self):
        self.temp.cleanup()
        self.assertFalse(Path(self.temp.name).exists())

    def create(self, **patch):
        body = {'request_id': str(uuid.uuid4()), 'title': 'Outline',
                'brief': 'Mira holds the key.\nShe opens the door.', 'asset_ids': []}
        body.update(patch)
        return body, storyboard_sources.create(self.board, self.w, body)

    def test_outline_is_independent_idempotent_and_hands_off_without_acceptance(self):
        request, result = self.create()
        source = result['source']['screenplay_revision_id']
        self.assertFalse(result['source']['accepted'])
        self.assertEqual(result, storyboard_sources.create(self.board, self.w, request))
        self.assertEqual(len(result['board']['body']['shots']), 2)
        self.assertEqual(len(storyboard_sources.list_sources(self.board, self.w)['sources']), 1)
        snapshot = projects.sql_snapshot(self.root / projects.DATABASES[0], self.w)
        self.assertEqual(snapshot['story_board_sources'][0]['source_id'], source)
        self.assertTrue(self.story.get_screenplay_revision(self.w, self.r)['accepted'])
        body = result['board']['body']
        body['shots']['1.1'].update(route='t2v', duration=6)
        self.board.save(self.w, source, {'expected_revision': 1, 'body': body})
        handoff = self.board.video_handoff(self.w, source, '1.1')
        self.assertEqual(handoff['source_kind'], 'brief_media')
        self.assertEqual(handoff['prompt'], 'Mira holds the key.')
        with self.assertRaises(LedgerConflict):
            storyboard_sources.create(self.board, self.w, {**request, 'title': 'Changed'})

    def test_media_outline_assembles_existing_editor_and_rejects_foreign_media(self):
        _, result = self.create(brief='', asset_ids=[self.asset['asset_id']])
        source = result['source']['screenplay_revision_id']
        shot = result['board']['body']['shots']['1.1']
        self.assertEqual((shot['route'], shot['duration']), ('existing', 2))
        editor = self.board.editor_handoff(self.w, source)
        self.assertEqual(editor['selection'][0]['asset_id'], self.asset['asset_id'])
        with self.assertRaises(ValueError):
            self.create(asset_ids=['foreign'])
        with self.assertRaisesRegex(ValueError, '6001'):
            self.create(brief='x' * 6001)

    def test_backlot_proposal_preserves_saved_state_and_blocks_stale_or_identity_edits(self):
        _, result = self.create(brief='', asset_ids=[self.asset['asset_id']])
        source = result['source']['screenplay_revision_id']
        session = interface_sessions.create(self.root, 'backlot', (self.w, source))
        self.addCleanup(lambda: interface_sessions.close(session))
        production_board.sync(self.board, session, 1)
        path = session['folder'] / 'projects/production/vibe-proposal.json'
        value = {'base_revision': 1, 'changes': [{'shot_key': '1.1', 'values': {'notes': 'From Backlot', 'duration': 1.5}}]}
        path.write_text(json.dumps(value))
        proposal = production_board.proposal(self.board, session)
        self.assertEqual(proposal['body']['shots']['1.1']['duration'], 1.5)
        self.assertEqual(self.board.get(self.w, source), result['board'])
        value['changes'][0]['values'] = {'media_asset_id': 'foreign'}
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'identities'):
            production_board.proposal(self.board, session)
        value['changes'][0]['values'] = {'duration': 1.5}
        path.write_text(json.dumps(value))
        self.board.save(self.w, source, {'expected_revision': 1, 'body': result['board']['body']})
        with self.assertRaisesRegex(ValueError, 'changed'):
            production_board.proposal(self.board, session)
