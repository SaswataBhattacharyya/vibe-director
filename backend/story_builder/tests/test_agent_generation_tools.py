"""Generation gateway acceptance with a fake native queue, never model execution."""
from story_builder.tests.test_agent_tasks import AgentTaskFixture
from story_builder.services import agent_generation_tools as generation, video_repertoire
from story_builder.services.production_ledger import LedgerConflict
from story_builder.services import media_library
from PIL import Image
import io


class GenerationGatewayTests(AgentTaskFixture):
    def test_fflf_owned_endpoints_are_frozen_in_order_and_never_auto_submitted(self):
        self.tasks.native_request = generation.bridge(self.app)
        images = []
        for color in ('red', 'blue'):
            stream = io.BytesIO()
            Image.new('RGB', (64, 64), color).save(stream, format='PNG')
            images.append(media_library.register_upload(self.root, self.owner,
                filename=color + '.png', content=stream.getvalue(), role='image_candidate'))
        template = generation.context()['video_templates'][2]
        first, last = [{k: image[k] for k in ('asset_id', 'sha256')} for image in images]
        payload = {'tool_id': 'video.generate', 'asset_ids': [i['asset_id'] for i in images],
            'settings': {'request': {**template, 'prompt': 'The red sky changes to blue.', 'first_frame': first, 'last_frame': last}}}
        row = self.tasks.propose(self.owner, payload)
        self.assertEqual(row['plan']['settings']['request']['first_frame'], first)
        self.assertEqual(row['plan']['settings']['request']['last_frame'], last)
        self.dispatch.assert_not_called()
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        payload['asset_ids'] = [first['asset_id']]
        with self.assertRaisesRegex(ValueError, 'Attach exactly'):
            self.tasks.propose(self.owner, payload)

    def setUp(self):
        super().setUp()
        self.calls = []
        self.done = False
        def bridge(method, path, body=None):
            self.calls.append((method, path, body))
            if path.endswith('/validations'):
                return {'ok': True}
            if path == '/api/images/jobs':
                return {'batch_id': 'batch-test'}
            return {'jobs': [{'status': 'completed' if self.done else 'queued', 'output_asset_id': None}]}
        self.tasks.native_request = bridge

    def draft_image(self):
        return self.tasks.propose(self.owner, {'tool_id': 'image.generate', 'asset_ids': [],
            'settings': {'workflow_id': 'z_image_turbo', 'prompt': 'A blue square', 'seed': 1,
                'width': 512, 'height': 512, 'steps': 9, 'cfg': 1}})

    def test_validation_inert_exact_approval_poll_and_no_duplicate(self):
        row = self.draft_image()
        self.assertEqual([p for _, p, _ in self.calls], ['/api/images/validations'])
        self.dispatch.assert_not_called()
        with self.assertRaises(LedgerConflict):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        result = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.assertEqual(result['status'], 'running')
        self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.assertEqual(sum(path == '/api/images/jobs' for _, path, _ in self.calls), 1)
        self.done = True
        self.assertEqual(self.tasks.poll(self.owner, row['task_id'])['status'], 'completed')

    def test_ambiguous_submission_never_repeats_or_claims_cancelled(self):
        row = self.draft_image()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        def lost(method, path, body=None):
            self.calls.append((method, path, body))
            if path.endswith('/validations'):
                return {'ok': True}
            raise OSError('response lost')
        self.tasks.native_request = lost
        with self.assertRaises(OSError):
            self.tasks.run(self.owner, row['task_id'], self.approval(row))
        result = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        self.assertEqual(result['status'], 'recovery_required')
        self.assertEqual(sum(path == '/api/images/jobs' for _, path, _ in self.calls), 1)
        with self.assertRaises(LedgerConflict):
            self.tasks.cancel(self.owner, row['task_id'])

    def test_provenance_tamper_rejected(self):
        row = self.draft_image()
        self.tasks.approve(self.owner, row['task_id'], self.approval(row))
        started = self.tasks.run(self.owner, row['task_id'], self.approval(row))
        job = video_repertoire.read_job(generation.KIND, started['invocation']['job_id'])
        job['request']['workspace_id'] = 'other-project'
        video_repertoire._atomic_json(video_repertoire.job_path(generation.KIND, job['job_id']), job)
        with self.assertRaises(LedgerConflict):
            self.tasks.poll(self.owner, row['task_id'])

    def test_real_validation_bridge_freezes_graph_and_rejects_invalid_settings(self):
        self.tasks.native_request = generation.bridge(self.app)
        row = self.draft_image()
        self.assertEqual(len(row['plan']['settings']['validation_sha256']), 64)
        self.assertEqual(row['plan']['settings'], self.draft_image()['plan']['settings'])
        template = generation.context()['video_templates'][0]
        video = self.tasks.propose(self.owner, {'tool_id': 'video.generate', 'asset_ids': [],
            'settings': {'request': {**template, 'prompt': 'A quiet street at dusk.'}}})
        self.assertEqual(video['plan']['settings']['request']['prompt'], 'A quiet street at dusk.')
        with self.assertRaises(ValueError):
            self.tasks.propose(self.owner, {'tool_id': 'image.generate', 'asset_ids': [],
                'settings': {'workflow_id': 'z_image_turbo', 'prompt': 'Square', 'seed': 1,
                    'width': 1, 'height': 512, 'steps': 9, 'cfg': 1}})
        self.dispatch.assert_not_called()
