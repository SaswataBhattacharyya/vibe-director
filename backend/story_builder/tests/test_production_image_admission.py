from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_image_worker import _advance_checked_image_stage, _director_acceptor
from story_builder.isolated_server import R2V_WORKFLOW_ID, _unresolved_opted_in_voice_ids, create_app
from story_builder.services.production_image_admission import (
    build_clip_frame_image_batches, build_entity_image_batches, build_world_view_image_batch,
)
from story_builder.services.isolated_video_jobs import story_clip_id
from story_builder.services.production_image_jobs import ProductionImageJobStore
from story_builder.services.production_image_selection import ProductionImageSelection
from story_builder.services.production_image_worker import ProductionImageWorkerSupervisor


class FakeStory:
    def __init__(self, accepted=True):
        self.accepted = accepted

    def get_screenplay_revision(self, project_id, revision_id):
        return {"accepted": self.accepted, "source_revision_id": "source-1", "graph_snapshot_id": "graph-1",
            "style_selection_snapshot_id": None, "screenplay": {"scenes": [{"scene_number": 1,
                "shots": [{"shot_number": 1}]}]}}

    def frame_revision(self, revision_id):
        return {"accepted": self.accepted, "source_revision_id": "source-1", "graph_snapshot_id": "graph-1",
            "style_selection_snapshot_id": None, "screenplay": {"scenes": [{"scene_number": 1,
            "shots": [{"shot_number": 1}]}]}}

    def get_story_graph(self, *, workspace_id, snapshot_id=None):
        return {"status": "complete", "records": [
            {"kind": "entity", "type": "CHARACTER", "record_id": "char-1"},
            {"kind": "entity", "type": "LOCATION", "record_id": "loc-1"}]}


class FakeSetup:
    def __init__(self, setup):
        self.setup = setup

    def get(self, *_args):
        return {"setup": self.setup}

    def frame_preparation_is_skipped(self, *_args):
        return False


def saved_setup():
    return {"mode": "assisted_manual", "automate_steps": {"character_images": True,
        "character_voice": False, "world_images": False, "frame_images": False, "video": False},
        "video_quality": "standard", "duration_policy": {"kind": "fixed", "seconds": 5},
        "image_stage_settings": {"character_images": {"workflow_id": "z_image_turbo",
            "width": 1280, "height": 720, "steps": 8, "cfg": 1.0}}}


class ProductionImageAdmissionTests(unittest.TestCase):
    def test_noop_character_admission_durably_advances_without_a_page(self):
        from story_builder.services.production_ledger import ProductionLedger
        for already_selected in (False, True):
            with self.subTest(already_selected=already_selected), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / 'runtime').mkdir()
                (root / 'runtime/isolated-image-worker-status.json').write_text(json.dumps({
                    'enabled': True, 'pid': os.getpid(), 'state': 'running', 'updated_unix': time.time()}))
                app = create_app(data_root=root)
                setup = saved_setup()
                setup['automate_steps']['world_images'] = True
                workspace, revision_id = 'story-0123456789ab', 'sp-1'
                ledger = ProductionLedger(root / 'services/production/ledger.sqlite3')
                with ledger._connect() as db:
                    db.execute('INSERT INTO story_production_setups(workspace_id,screenplay_revision_id,setup_json) VALUES(?,?,?)',
                        (workspace, revision_id, json.dumps(setup)))
                store = ProductionImageJobStore(root / 'services/production/image-jobs.sqlite3')
                selections = ProductionImageSelection(root / 'services/production/image-jobs.sqlite3')
                records = [{'kind': 'entity', 'type': 'location', 'record_id': 'loc-1'}]
                if already_selected:
                    records.append({'kind': 'entity', 'type': 'character', 'record_id': 'char-1'})
                    selections.select(project_id=workspace, screenplay_revision_id=revision_id,
                        target_type='character', target_record_id='char-1', asset_id='saved-character',
                        job_id='saved-job', authority='director')
                revision = {'accepted': True, 'screenplay_revision_id': revision_id,
                    'source_revision_id': 'source-1', 'graph_snapshot_id': 'graph-1'}
                body = json.dumps({'workspace_id': workspace, 'screenplay_revision_id': revision_id,
                    'step': 'character_images'}).encode()
                statuses = []
                with patch('story_builder.isolated_server.ProductionSetup.get', return_value={'setup': setup}), \
                     patch('story_builder.isolated_server.StoryAuthoring.get_screenplay_revision', return_value=revision), \
                     patch('story_builder.isolated_server.StoryAuthoring.get_story_graph', return_value={'status': 'complete', 'records': records}), \
                     patch('story_builder.isolated_server.image_workflow_catalog', return_value={'workflows': [
                        {'workflow_id': 'z_image_turbo', 'automation_available': True}]}), \
                     patch('story_builder.isolated_server._runtime_guard', return_value={'safe_to_submit': True}), \
                     patch('story_builder.services.reasoning_provider.provider_catalog', return_value={'provider': 'codex', 'providers': [
                        {'id': 'codex', 'available': True}]}):
                    result = json.loads(b''.join(app({'REQUEST_METHOD': 'POST',
                        'PATH_INFO': '/api/images/automated-stage', 'QUERY_STRING': '',
                        'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(body)),
                        'wsgi.input': io.BytesIO(body)}, lambda status, headers: statuses.append(status))))
                self.assertEqual(statuses, ['200 OK'])
                self.assertEqual(result['batches'], [])
                self.assertTrue(result['run_id'])
                with store._connect() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM production_image_jobs').fetchone()[0], 0)
                story = FakeStory()
                story.ledger = ledger
                story.get_story_graph = lambda **kwargs: {'status': 'complete', 'records': records}
                with patch('story_builder.isolated_image_worker.ProductionSetup.list_assisted_stage_skips',
                        return_value={'skipped': []}), \
                     patch('story_builder.isolated_image_worker._request_json', return_value={'step': 'world_images'}) as request:
                    resumed = _advance_checked_image_stage(root=root, ledger=ledger, story=story,
                        selections=selections, image_jobs=store)
                self.assertEqual(resumed['step'], 'world_images')
                request.assert_called_once()

    def _get(self, app, path, query=""):
        response = []
        environ = {"REQUEST_METHOD": "GET", "PATH_INFO": path, "QUERY_STRING": query,
            "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b"")}
        result = json.loads(b"".join(app(environ, lambda status, headers: response.append(status))))
        return response[0], result

    def test_image_workflow_gpu_preflight_reports_available_memory_without_submitting_work(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            catalog = {"workflows": [{"workflow_id": "z_image_turbo", "available": True}], "generation_policy": {}}
            host_memory = {"total_gib": 128.0, "available_gib": 101.0,
                "swap_total_gib": 16.0, "swap_free_gib": 16.0}
            runtime = {"comfyui": {"free_gib": 23.5}, "recorded_at": "2026-10-12T00:00:00+00:00"}
            with patch("story_builder.isolated_server.image_workflow_catalog", return_value=catalog), \
                 patch("story_builder.isolated_server.inspect_gpu_runtime", return_value=runtime) as inspect, \
                 patch("story_builder.isolated_server.read_host_memory_diagnostic", return_value=host_memory):
                status, result = self._get(app, "/api/images/workflows", "check_gpu_admission=1")
            self.assertEqual(status, "200 OK")
            self.assertEqual(result["workflows"], catalog["workflows"])
            self.assertEqual(result["gpu_admission"], {"available": True, "checked": True,
                "free_gib": 23.5, "host_memory": host_memory, "required_gib": 0.0,
                "checked_at": runtime["recorded_at"], "reason": None})
            inspect.assert_called_once()

    def test_opted_in_voice_choices_block_direct_assisted_video_start(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = create_app(data_root=root)
            setup = {"mode": "assisted_manual", "automate_steps": {"character_voice": True,
                "video": True}, "video_workflow_id": R2V_WORKFLOW_ID}
            from contextlib import closing
            with closing(sqlite3.connect(root / "services/production/ledger.sqlite3")) as db:
                db.execute("INSERT INTO story_production_setups(workspace_id,screenplay_revision_id,setup_json) VALUES(?,?,?)",
                    ("story-0123456789ab", "sp-1", json.dumps(setup)))
                db.commit()
            payload = {"screenplay_revision_id": "sp-1"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST",
                "PATH_INFO": "/api/story/workspaces/story-0123456789ab/assisted-video-run",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json",
                "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            voice_state = {"characters": [{"record_id": "speaker-a"}], "automation_decisions": [{
                "character_id": "speaker-a", "status": "unmatched"}], "bindings": [],
                "speech_statuses": [{"character_id": "speaker-a", "status": "speaking"},
                    {"character_id": "quiet", "status": "not_speaking"}]}
            with patch("story_builder.isolated_server.CharacterVoiceBindings.get", return_value=voice_state):
                result = json.loads(b"".join(app(environ,
                    lambda status, headers: response.append(status))))
            self.assertEqual(response[0], "409 Conflict")
            self.assertIn("Resolve the opted-in voice choices", result["error"]["message"])
            self.assertEqual(_unresolved_opted_in_voice_ids(voice_state), ["speaker-a"])

    def test_durable_image_owner_admits_next_checked_stage_without_a_page(self):
        import sqlite3

        class FakeLedger:
            def __init__(self, path):
                self.path = path

            def _connect(self):
                db = sqlite3.connect(self.path)
                db.row_factory = sqlite3.Row
                return db

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger_path = root / "ledger.sqlite3"
            ledger = FakeLedger(ledger_path)
            with ledger._connect() as db:
                db.execute("CREATE TABLE story_production_setups(workspace_id TEXT, screenplay_revision_id TEXT, setup_json TEXT, updated_at TEXT)")
                db.execute("CREATE TABLE production_runs(project_id TEXT, config_json TEXT, created_at TEXT)")
                setup = {"mode": "assisted_manual", "automate_steps": {
                    "character_images": True, "character_voice": False, "world_images": True,
                    "frame_images": False, "video": False}, "image_stage_settings": {
                    "character_images": {"workflow_id": "z_image_turbo"},
                    "world_images": {"workflow_id": "z_image_turbo", "world_view_count": 4}}}
                db.execute("INSERT INTO story_production_setups VALUES(?,?,?,?)",
                    ("story-1", "sp-1", json.dumps(setup), "2026-10-13T00:00:00Z"))
            store = ProductionImageJobStore(root / "image-jobs.sqlite3")
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            admitted = store.enqueue_batch(project_id="story-1", run_id="run-1", idempotency_key="char-stage-1",
                workflow_id="z_image_turbo", workflow_version="1", asset_role="character_master",
                prompt="character", settings={"stage": "character_images", "setup_sha256": setup_hash,
                    "lineage": {"screenplay_revision_id": "sp-1"}},
                candidates=[{"seed": 1, "graph": {"1": {"class_type": "Test"}}}])
            with store._connect() as db:
                db.execute("UPDATE production_image_jobs SET status='completed' WHERE job_id=?",
                    (admitted["jobs"][0]["job_id"],))
            selections = ProductionImageSelection(root / "image-jobs.sqlite3")
            selections.select(project_id="story-1", screenplay_revision_id="sp-1",
                target_type="character", target_record_id="char-1", asset_id="asset-char",
                job_id="job-char", authority="director")
            story = FakeStory()
            story.ledger = ledger
            with patch("story_builder.isolated_image_worker.ProductionSetup.list_assisted_stage_skips",
                    return_value={"skipped": []}), \
                 patch("story_builder.isolated_image_worker._request_json", return_value={"step": "world_images"}) as request:
                result = _advance_checked_image_stage(root=root, ledger=ledger,
                    story=story,
                    selections=selections, image_jobs=store)
            self.assertEqual(result["step"], "world_images")
            request.assert_called_once_with("http://127.0.0.1:3020/api/images/automated-stage",
                method="POST", payload={"workspace_id": "story-1", "screenplay_revision_id": "sp-1",
                    "step": "world_images"}, timeout_seconds=30)

    def test_durable_image_owner_waits_until_previous_targets_are_saved(self):
        import sqlite3

        class FakeLedger:
            def __init__(self, path): self.path, self.connections = path, []
            def _connect(self):
                db = sqlite3.connect(self.path)
                db.row_factory = sqlite3.Row
                self.connections.append(db)
                return db
            def close(self):
                for db in self.connections:
                    try: db.close()
                    except sqlite3.Error: pass

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = FakeLedger(root / "ledger.sqlite3")
            setup = {"mode": "assisted_manual", "automate_steps": {
                "character_images": True, "character_voice": False, "world_images": True,
                "frame_images": False, "video": False}, "image_stage_settings": {}}
            with ledger._connect() as db:
                db.execute("CREATE TABLE story_production_setups(workspace_id TEXT, screenplay_revision_id TEXT, setup_json TEXT, updated_at TEXT)")
                db.execute("CREATE TABLE production_runs(project_id TEXT, config_json TEXT, created_at TEXT)")
                db.execute("INSERT INTO story_production_setups VALUES(?,?,?,?)",
                    ("story-1", "sp-1", json.dumps(setup), "2026-10-13T00:00:00Z"))
            store = ProductionImageJobStore(root / "image-jobs.sqlite3")
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            admitted = store.enqueue_batch(project_id="story-1", run_id="run-1", idempotency_key="char-stage-1",
                workflow_id="z_image_turbo", workflow_version="1", asset_role="character_master",
                prompt="character", settings={"stage": "character_images", "setup_sha256": setup_hash,
                    "lineage": {"screenplay_revision_id": "sp-1"}},
                candidates=[{"seed": 1, "graph": {"1": {"class_type": "Test"}}}])
            with store._connect() as db:
                db.execute("UPDATE production_image_jobs SET status='completed' WHERE job_id=?",
                    (admitted["jobs"][0]["job_id"],))
            selections = ProductionImageSelection(root / "image-jobs.sqlite3")
            story = FakeStory()
            story.ledger = ledger
            with patch("story_builder.isolated_image_worker.ProductionSetup.list_assisted_stage_skips",
                    return_value={"skipped": []}), \
                 patch("story_builder.isolated_image_worker._request_json") as request:
                result = _advance_checked_image_stage(root=root, ledger=ledger,
                    story=story,
                    selections=selections, image_jobs=store)
            self.assertIsNone(result)
            request.assert_not_called()
            selections.select(project_id="story-1", screenplay_revision_id="sp-1",
                target_type="character", target_record_id="char-1", asset_id="asset-char",
                job_id="job-char", authority="director")
            # A fresh callback has no process-local state; it resumes from the saved selection.
            with patch("story_builder.isolated_image_worker.ProductionSetup.list_assisted_stage_skips",
                    return_value={"skipped": []}), \
                 patch("story_builder.isolated_image_worker._request_json",
                    return_value={"step": "world_images"}) as resumed_request:
                resumed = _advance_checked_image_stage(root=root, ledger=ledger,
                    story=story, selections=selections, image_jobs=store, retry_after={})
            self.assertEqual(resumed["step"], "world_images")
            resumed_request.assert_called_once()

    def test_durable_image_owner_starts_video_after_checked_image_stages_are_complete(self):
        from contextlib import contextmanager
        import sqlite3

        class FakeLedger:
            def __init__(self, path): self.path = path
            @contextmanager
            def _connect(self):
                db = sqlite3.connect(self.path)
                db.row_factory = sqlite3.Row
                try:
                    yield db
                    db.commit()
                finally: db.close()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = FakeLedger(root / "ledger.sqlite3")
            setup = {"mode": "assisted_manual", "automate_steps": {
                "character_images": True, "character_voice": False, "world_images": False,
                "frame_images": False, "video": True}, "video_workflow_id": "minimax_h3_r2v_dynamic_v1",
                "image_stage_settings": {}}
            with ledger._connect() as db:
                db.execute("CREATE TABLE story_production_setups(workspace_id TEXT, screenplay_revision_id TEXT, setup_json TEXT, updated_at TEXT)")
                db.execute("CREATE TABLE production_runs(project_id TEXT, config_json TEXT, created_at TEXT)")
                db.execute("INSERT INTO story_production_setups VALUES(?,?,?,?)",
                    ("story-1", "sp-1", json.dumps(setup), "2026-10-13T00:00:00Z"))
            store = ProductionImageJobStore(root / "image-jobs.sqlite3")
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            store.enqueue_batch(project_id="story-1", run_id="run-1", idempotency_key="char-stage-1",
                workflow_id="z_image_turbo", workflow_version="1", asset_role="character_master",
                prompt="character", settings={"stage": "character_images", "setup_sha256": setup_hash,
                    "lineage": {"screenplay_revision_id": "sp-1"}},
                candidates=[{"seed": 1, "graph": {"1": {"class_type": "Test"}}}])
            story = FakeStory()
            story.ledger = ledger
            selections = ProductionImageSelection(root / "image-jobs.sqlite3")
            with patch("story_builder.isolated_image_worker._image_stage_is_complete", return_value=True), \
                 patch("story_builder.isolated_image_worker._request_json",
                    side_effect=[{"run_state": "not_started"}, {"run_state": "queued"}]) as request:
                result = _advance_checked_image_stage(root=root, ledger=ledger, story=story,
                    selections=selections, image_jobs=store)
            self.assertEqual(result["step"], "video")
            self.assertEqual(request.call_count, 2)
            self.assertTrue(request.call_args_list[0].args[0].endswith(
                "/api/story/workspaces/story-1/assisted-video-run?screenplay_revision_id=sp-1"))
            self.assertEqual(request.call_args_list[1].kwargs["method"], "POST")

    def test_durable_image_owner_waits_for_unchecked_stage_or_explicit_skip(self):
        import sqlite3

        class FakeLedger:
            def __init__(self, path): self.path, self.connections = path, []
            def _connect(self):
                db = sqlite3.connect(self.path)
                db.row_factory = sqlite3.Row
                self.connections.append(db)
                return db
            def close(self):
                for db in self.connections:
                    try: db.close()
                    except sqlite3.Error: pass

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = FakeLedger(root / "ledger.sqlite3")
            setup = {"mode": "assisted_manual", "automate_steps": {
                "character_images": True, "character_voice": False, "world_images": False,
                "frame_images": True, "video": False}, "image_stage_settings": {}}
            with ledger._connect() as db:
                db.execute("CREATE TABLE story_production_setups(workspace_id TEXT, screenplay_revision_id TEXT, setup_json TEXT, updated_at TEXT)")
                db.execute("CREATE TABLE production_runs(project_id TEXT, config_json TEXT, created_at TEXT)")
                db.execute("INSERT INTO story_production_setups VALUES(?,?,?,?)",
                    ("story-1", "sp-1", json.dumps(setup), "2026-10-13T00:00:00Z"))
            store = ProductionImageJobStore(root / "image-jobs.sqlite3")
            setup_hash = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            store.enqueue_batch(project_id="story-1", run_id="run-1", idempotency_key="char-stage-1",
                workflow_id="z_image_turbo", workflow_version="1", asset_role="character_master",
                prompt="character", settings={"stage": "character_images", "setup_sha256": setup_hash,
                    "lineage": {"screenplay_revision_id": "sp-1"}},
                candidates=[{"seed": 1, "graph": {"1": {"class_type": "Test"}}}])
            story = FakeStory()
            story.ledger = ledger
            from story_builder import isolated_image_worker as image_worker
            original_complete = image_worker._image_stage_is_complete
            def complete(**kwargs):
                if kwargs["step"] == "character_images":
                    return True
                return original_complete(**kwargs)
            with patch("story_builder.isolated_image_worker.ProductionSetup.list_assisted_stage_skips",
                    return_value={"skipped": []}), \
                 patch("story_builder.isolated_image_worker._image_stage_is_complete", side_effect=complete), \
                 patch("story_builder.isolated_image_worker._request_json") as request:
                result = _advance_checked_image_stage(root=root, ledger=ledger, story=story,
                    selections=ProductionImageSelection(root / "image-jobs.sqlite3"), image_jobs=store)
            self.assertEqual(result["status"], "waiting_for_manual")
            self.assertEqual(result["step"], "world_images")
            request.assert_not_called()

            with patch("story_builder.isolated_image_worker.ProductionSetup.list_assisted_stage_skips",
                    return_value={"skipped": ["world_images"]}), \
                 patch("story_builder.isolated_image_worker.ProductionSetup.list_frame_preparation_skips",
                    return_value={"skipped": []}), \
                 patch("story_builder.isolated_image_worker._image_stage_is_complete", side_effect=complete), \
                 patch("story_builder.isolated_image_worker._request_json", return_value={"step": "frame_images"}) as request:
                result = _advance_checked_image_stage(root=root, ledger=ledger, story=story,
                    selections=ProductionImageSelection(root / "image-jobs.sqlite3"), image_jobs=store)
            ledger.close()
            self.assertEqual(result["step"], "frame_images")
            request.assert_called_once_with("http://127.0.0.1:3020/api/images/automated-stage",
                method="POST", payload={"workspace_id": "story-1", "screenplay_revision_id": "sp-1",
                    "step": "frame_images"}, timeout_seconds=30)

    def test_image_supervisor_checks_durable_progression_while_idle(self):
        class IdleWorker:
            def reconcile_recovery_once(self): return {"observed": 0}
            def process_one(self): return {"status": "idle"}
            def review_next_candidate(self): return {"status": "idle"}

        calls = []
        supervisor = None

        def advance():
            calls.append("checked")
            supervisor._stop.set()

        supervisor = ProductionImageWorkerSupervisor(IdleWorker(), advance_assisted_stages=advance)
        supervisor._run()
        self.assertEqual(calls, ["checked"])

    def test_image_workflow_gpu_preflight_reports_runtime_failure_as_a_separate_block(self):
        from story_builder.services.gpu_runtime import GPUAdmissionError
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            catalog = {"workflows": [{"workflow_id": "z_image_turbo", "available": True}], "generation_policy": {}}
            with patch("story_builder.isolated_server.image_workflow_catalog", return_value=catalog), \
                 patch("story_builder.isolated_server.inspect_gpu_runtime",
                       side_effect=GPUAdmissionError("GPU operating limit reached; submission withheld.")), \
                 patch("story_builder.isolated_server.read_host_memory_diagnostic",
                       return_value={"total_gib": 128.0, "available_gib": 101.0,
                           "swap_total_gib": 16.0, "swap_free_gib": 16.0}):
                status, result = self._get(app, "/api/images/workflows", "check_gpu_admission=1")
            self.assertEqual(status, "200 OK")
            self.assertTrue(result["workflows"][0]["available"])
            self.assertEqual(result["gpu_admission"]["available"], False)
            self.assertEqual(result["gpu_admission"]["required_gib"], 0.0)
            self.assertEqual(result["gpu_admission"]["host_memory"]["available_gib"], 101.0)
            self.assertIn("operating limit", result["gpu_admission"]["reason"])

    def test_automated_image_stage_requires_verified_smoke_even_when_manual_is_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            payload = {"workspace_id": "story-0123456789ab", "screenplay_revision_id": "sp-1",
                "step": "character_images"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/automated-stage",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            catalog = {"workflows": [{"workflow_id": "z_image_turbo", "available": True,
                "automation_available": False,
                "automation_disabled_reason": "Run this workflow manually once."}]}
            with patch("story_builder.isolated_server.ProductionSetup.get",
                    return_value={"setup": saved_setup()}), \
                 patch("story_builder.isolated_server.image_workflow_catalog", return_value=catalog):
                result = json.loads(b"".join(app(environ,
                    lambda status, headers: response.append(status))))
            self.assertEqual(response[0], "503 Service Unavailable")
            self.assertIn("manually once", result["error"]["message"])

    def test_automated_image_route_rejects_a_stage_the_saved_setup_did_not_enable(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_root=Path(temporary))
            payload = {"workspace_id": "story-0123456789ab", "screenplay_revision_id": "sp-1",
                "step": "world_images"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/automated-stage",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server.ProductionSetup.get", return_value={"setup": saved_setup()}):
                result = json.loads(b"".join(app(environ, lambda status, headers: response.append(status))))
            self.assertEqual(response[0], "409 Conflict")
            self.assertIn("not enabled", result["error"]["message"])

    def test_automated_world_views_use_the_selected_master_and_configured_count(self):
        setup = saved_setup()
        setup["automate_steps"]["world_images"] = True
        setup["image_stage_settings"]["world_images"] = {"workflow_id": "z_image_turbo",
            "world_view_count": 8}
        screenplay = {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
            "graph_snapshot_id": "graph-1", "style_selection_snapshot_id": None}
        target = {"kind": "entity", "type": "LOCATION", "record_id": "loc-1", "name": "Old station",
            "detail": "Rain-dark brick platform."}
        master = {"asset_id": "asset-master", "sha256": "a" * 64, "roles": ["world_master"]}
        knowledge = {"workflow_id": "qwen_image_multi_angle_2511", "guidance_version": "2",
            "source_ids": ["qwen-multi-angle"]}
        batch = build_world_view_image_batch(workspace_id="story-1", screenplay=screenplay,
            setup={"setup": setup}, target=target, base_asset=master, prompt="Rotate around the platform.",
            knowledge_ref=knowledge, run_id="run-1")
        self.assertEqual(batch["workflow_id"], "qwen_image_multi_angle_2511")
        self.assertEqual(batch["asset_role"], "world_view")
        self.assertEqual(len(batch["candidates"]), 8)
        self.assertEqual([item["label"] for item in batch["settings"]["world_views"]],
            ["Front", "Front-right", "Right", "Back-right", "Back", "Back-left", "Left", "Front-left"])
        self.assertEqual([item["world_view"] for item in batch["candidates"]], batch["settings"]["world_views"])
        self.assertEqual(batch["settings"]["image_references"], [{"asset_id": "asset-master", "sha256": "a" * 64}])
        self.assertEqual(batch["settings"]["lineage"]["target_record_id"], "loc-1")
        self.assertEqual(batch["settings"]["prompt_knowledge_ref"], knowledge)
        selected_style = {"directing_style": {"style_id": "noir", "display_name": "Noir",
            "style_version_id": "noir:v1", "version": 1, "guidance": "Keep the world stark."}}
        styled = build_world_view_image_batch(workspace_id="story-1", screenplay=screenplay,
            setup={"setup": setup}, target=target, base_asset=master, prompt="Rotate around the platform.",
            knowledge_ref=knowledge, run_id="run-1", style_selection=selected_style)
        self.assertIn("Keep the world stark", styled["prompt"])
        self.assertNotEqual(batch["idempotency_key"], styled["idempotency_key"])
        self.assertEqual(styled["settings"]["lineage"]["style_selection"]["directing_style"]["style_version_id"], "noir:v1")
        self.assertEqual(batch["idempotency_key"], build_world_view_image_batch(workspace_id="story-1",
            screenplay=screenplay, setup={"setup": setup}, target=target, base_asset=master,
            prompt="A changed prompt is not part of batch identity.", knowledge_ref=knowledge,
            run_id="retry")["idempotency_key"])

    def test_automated_world_views_reject_unchecked_or_non_master_inputs(self):
        setup = saved_setup()
        setup["image_stage_settings"]["world_images"] = {"workflow_id": "z_image_turbo", "world_view_count": 4}
        args = {"workspace_id": "story-1", "screenplay": {"screenplay_revision_id": "sp-1"},
            "setup": {"setup": setup}, "target": {"kind": "entity", "type": "location", "record_id": "loc-1"},
            "base_asset": {"asset_id": "asset", "sha256": "b" * 64, "roles": ["world_master"]},
            "prompt": "Four directions.", "knowledge_ref": {}, "run_id": "run-1"}
        with self.assertRaisesRegex(ValueError, "Assisted manual setup"):
            build_world_view_image_batch(**args)
        setup["automate_steps"]["world_images"] = True
        with self.assertRaisesRegex(ValueError, "selected location"):
            build_world_view_image_batch(**{**args, "base_asset": {**args["base_asset"], "roles": ["image_candidate"]}})

    def test_world_base_can_start_before_optional_multi_angle_followup_is_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runtime").mkdir()
            (root / "runtime/isolated-image-worker-status.json").write_text(json.dumps({
                "enabled": True, "pid": os.getpid(), "state": "running", "updated_unix": time.time()}))
            app = create_app(data_root=root)
            setup = saved_setup()
            setup["automate_steps"]["world_images"] = True
            setup["image_stage_settings"]["world_images"] = {"workflow_id": "z_image_turbo",
                "width": 1280, "height": 720, "steps": 8, "cfg": 1.0, "world_view_count": 4}
            payload = {"workspace_id": "story-0123456789ab", "screenplay_revision_id": "sp-1",
                "step": "world_images"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/automated-stage",
                "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server.ProductionSetup.get", return_value={"setup": setup}), \
                 patch("story_builder.isolated_server.StoryAuthoring.get_screenplay_revision", return_value={
                    "accepted": True, "screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
                    "graph_snapshot_id": "graph-1", "style_selection_snapshot_id": None,
                    "screenplay": {"scenes": []}}), \
                 patch("story_builder.isolated_server.StoryAuthoring.get_story_graph", return_value={
                    "status": "complete", "records": [{"kind": "entity", "type": "location",
                        "record_id": "loc-1", "name": "Station"}]}), \
                 patch("story_builder.isolated_server.image_workflow_catalog", return_value={"workflows": [{
                    "workflow_id": "z_image_turbo", "available": True,
                    "automation_available": True}]}), \
                 patch("story_builder.isolated_server._runtime_guard", return_value={"safe_to_submit": True}), \
                 patch("story_builder.services.reasoning_provider.provider_catalog", return_value={"provider": "codex", "providers": [{
                    "id": "codex", "available": True}]}):
                result = json.loads(b"".join(app(environ, lambda status, headers: response.append(status))))
            self.assertEqual(response[0], "202 Accepted", result)
            self.assertEqual(result["batches"][0]["jobs"][0]["asset_role"], "world_master")

    def test_checked_character_stage_admission_is_idempotent_and_fails_closed_on_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runtime").mkdir()
            (root / "runtime/isolated-image-worker-status.json").write_text(json.dumps({
                "enabled": True, "pid": os.getpid(), "state": "running", "updated_unix": time.time()}))
            drafts = []
            def provider(**kwargs):
                drafts.append(kwargs["prompt"])
                return {"prompt": "One human in a plain shirt and trousers, upright with empty hands against a plain white studio background."}
            app = create_app(data_root=root, reasoning_json_provider=provider)
            setup_state = {"setup": saved_setup()}
            graph = {"status": "complete", "records": [
                {"kind": "entity", "type": "character", "record_id": "char-a", "name": "Ada", "detail": "Pilot."},
                {"kind": "entity", "type": "character", "record_id": "char-b", "name": "Bo", "detail": "Mechanic."}]}
            payload = {"workspace_id": "story-0123456789ab", "screenplay_revision_id": "sp-1",
                "step": "character_images"}
            def request():
                body = json.dumps(payload).encode()
                response = []
                result = b"".join(app({"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/automated-stage",
                    "QUERY_STRING": "", "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)),
                    "wsgi.input": io.BytesIO(body)}, lambda status, headers: response.append(status)))
                return response[0], json.loads(result)

            with patch("story_builder.isolated_server.ProductionSetup.get", return_value=setup_state), \
                 patch("story_builder.isolated_server.StoryAuthoring.get_screenplay_revision", return_value={
                    "accepted": True, "screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
                    "graph_snapshot_id": "graph-1"}), \
                 patch("story_builder.isolated_server.StoryAuthoring.get_story_graph", return_value=graph), \
                 patch("story_builder.isolated_server.image_workflow_catalog", return_value={"workflows": [{
                    "workflow_id": "z_image_turbo", "available": True,
                    "automation_available": True}]}), \
                 patch("story_builder.isolated_server._runtime_guard", return_value={"safe_to_submit": True}), \
                 patch("story_builder.services.reasoning_provider.provider_catalog", return_value={"provider": "codex", "providers": [{
                    "id": "codex", "available": True}]}):
                status, result = request()
                self.assertEqual(status, "202 Accepted")
                self.assertEqual(result["target_count"], 2)
                self.assertEqual([len(batch["jobs"]) for batch in result["batches"]], [1, 1])
                retry_status, retry = request()
            self.assertEqual(retry_status, "202 Accepted")
            self.assertTrue(retry["reused"])
            self.assertEqual(len(drafts), 2)  # One per target; replay must not call the provider.
            self.assertTrue(all("omit the occupation/job title itself" in draft for draft in drafts))
            for batch in result["batches"]:
                for job in batch["jobs"]:
                    self.assertIn("empty hands", job["prompt"])
                    self.assertNotIn("Pilot", job["prompt"])
                    self.assertNotIn("Mechanic", job["prompt"])
            store = ProductionImageJobStore(root / "services/production/image-jobs.sqlite3")
            self.assertEqual(sum(len(store.list_batch(project_id="story-0123456789ab", batch_id=item["batch_id"])["jobs"])
                for item in result["batches"]), 2)

    @patch("story_builder.services.storyboard.FFLF_AUTOMATION_ENABLED", True)
    def test_checked_frame_stage_admission_skips_user_skipped_clips(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runtime").mkdir()
            (root / "runtime/isolated-image-worker-status.json").write_text(json.dumps({
                "enabled": True, "pid": os.getpid(), "state": "running", "updated_unix": time.time()}))
            app = create_app(data_root=root)
            setup = saved_setup()
            setup["automate_steps"].update(character_images=False, frame_images=True)
            setup["image_stage_settings"] = {"frame_images": dict(setup["image_stage_settings"]["character_images"])}
            setup_state = {"setup": setup}
            screenplay = {"accepted": True, "screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
                "graph_snapshot_id": "graph-1", "style_selection_snapshot_id": None,
                "screenplay": {"scenes": [{"scene_number": 1, "slugline": "INT. STATION",
                    "shots": [{"shot_number": 1, "action": "Mira enters."},
                              {"shot_number": 2, "action": "Train arrives."}]}]}}
            payload = {"workspace_id": "story-0123456789ab", "screenplay_revision_id": "sp-1", "step": "frame_images"}
            body = json.dumps(payload).encode()
            response = []
            environ = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/images/automated-stage", "QUERY_STRING": "",
                "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
            with patch("story_builder.isolated_server.ProductionSetup.get", return_value=setup_state), \
                 patch("story_builder.isolated_server.ProductionSetup.list_frame_preparation_skips", return_value={
                    "skipped": [{"scene_number": 1, "shot_number": 2}]}), \
                 patch("story_builder.isolated_server.StoryAuthoring.get_screenplay_revision", return_value=screenplay), \
                 patch("story_builder.isolated_server.StoryAuthoring.get_story_graph", return_value={"status": "complete", "records": []}), \
                 patch("story_builder.isolated_server.image_workflow_catalog", return_value={"workflows": [{
                    "workflow_id": "z_image_turbo", "available": True,
                    "automation_available": True}]}), \
                 patch("story_builder.isolated_server._runtime_guard", return_value={"safe_to_submit": True}), \
                 patch("story_builder.services.reasoning_provider.provider_catalog", return_value={"provider": "codex", "providers": [{
                    "id": "codex", "available": True}]}):
                result = json.loads(b"".join(app(environ, lambda status, headers: response.append(status))))
            self.assertEqual(response[0], "202 Accepted")
            self.assertEqual(result["target_count"], 2)
            jobs = [job for batch in result["batches"] for job in batch["jobs"]]
            self.assertEqual({job["asset_role"] for job in jobs}, {"first_frame", "last_frame"})
            self.assertTrue(all(job["settings"]["lineage"]["shot_number"] == 1 for job in jobs))

    def test_character_stage_builds_deterministic_per_target_director_batches(self):
        screenplay = {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
            "graph_snapshot_id": "graph-1", "screenplay": {"scenes": [{"slugline": "INT. HANGAR",
                "summary": "Ada returns to the hangar.", "shots": [{"action": "Ada removes her red coat."}]}]}}
        graph = {"status": "complete", "records": [
            {"kind": "entity", "type": "character", "record_id": "char-z", "name": "Zed", "detail": "Red coat."},
            {"kind": "entity", "type": "character", "record_id": "char-a", "name": "Ada", "detail": "Pilot."},
            {"kind": "entity", "type": "location", "record_id": "place", "name": "Dock"}]}
        kwargs = {"workspace_id": "story-0123456789ab", "screenplay": screenplay,
            "graph": graph, "setup": {"setup": saved_setup()}, "step": "character_images", "run_id": "run-1"}
        kwargs["style_selection"] = {"snapshot_id": "style-snapshot", "production_type": "neo_noir",
            "style_version_id": "base:neo_noir:v1", "narrative_hash": "a" * 64,
            "director_profile_hash": "b" * 64, "narrative_guidance": {"image": "Hard shadows and restrained colors."},
            "director_profile": {"purpose": "Keep scenes tense.", "behavior": ["Favor practical light."]},
            "directing_style": {"style_id": "horror", "display_name": "Horror", "style_version_id": "horror:v2",
                "version": 2, "guidance": "Build dread through negative space.", "style_hash": "c" * 64}}
        batches = build_entity_image_batches(**kwargs)
        self.assertEqual([batch["settings"]["lineage"]["target_record_id"] for batch in batches], ["char-a", "char-z"])
        self.assertEqual(len(batches[0]["candidates"]), 1)
        self.assertIn("plain white studio background", batches[0]["prompt"])
        world_setup = saved_setup()
        world_setup["automate_steps"]["world_images"] = True
        world_setup["image_stage_settings"]["world_images"] = dict(world_setup["image_stage_settings"]["character_images"])
        worlds = build_entity_image_batches(**{**kwargs, "step":"world_images", "setup":{"setup":world_setup}})
        self.assertIn("No people or characters", worlds[0]["prompt"])
        drafted_worlds = build_entity_image_batches(**{**kwargs, "step":"world_images", "setup":{"setup":world_setup}},
            world_prompt_drafter=lambda **_: "Owner-approved empty dock, worn concrete and diffuse daylight.")
        self.assertEqual(drafted_worlds[0]["prompt"], "Owner-approved empty dock, worn concrete and diffuse daylight.")
        self.assertEqual(drafted_worlds[0]["settings"], worlds[0]["settings"])
        for step, callback in [("character_images", "character_prompt_drafter"), ("world_images", "world_prompt_drafter")]:
            with self.subTest(step=step), self.assertRaisesRegex(ValueError, "Director did not prepare"):
                build_entity_image_batches(**{**kwargs, "step":step, "setup":{"setup":world_setup}, callback:lambda **_: None})
        self.assertTrue(batches[0]["settings"]["director_review_required"])
        self.assertEqual(batches[0]["settings"]["director_provider"], "codex")
        self.assertIn("Hard shadows and restrained colors", batches[0]["prompt"])
        self.assertIn("Directing style: Horror", batches[0]["prompt"])
        self.assertIn("Build dread through negative space", batches[0]["prompt"])
        self.assertIn("Ada returns to the hangar", batches[0]["prompt"])
        self.assertEqual(batches[0]["settings"]["lineage"]["style_selection"]["style_version_id"], "base:neo_noir:v1")
        self.assertEqual(batches[0]["settings"]["lineage"]["style_selection"]["directing_style"], {
            "style_id": "horror", "style_version_id": "horror:v2", "version": 2, "style_hash": "c" * 64})
        revised_style = {**kwargs, "style_selection": {**kwargs["style_selection"],
            "directing_style": {**kwargs["style_selection"]["directing_style"],
                "guidance": "Use brighter, open compositions."}}}
        revised = build_entity_image_batches(**revised_style)
        self.assertNotEqual(batches[0]["idempotency_key"], revised[0]["idempotency_key"])
        oversized = {**kwargs, "graph": {"status": "complete", "records": [
            {"kind": "entity", "type": "character", "record_id": "char-a", "name": "Ada", "detail": "x" * 9000}]}}
        with self.assertRaisesRegex(ValueError, "exceeds the 6,999-character image limit"):
            build_entity_image_batches(**oversized)
        self.assertEqual(batches, build_entity_image_batches(**kwargs))
        self.assertEqual(len(build_entity_image_batches(**kwargs, selected_targets={"char-a"})), 1)

    def test_admission_rejects_unchecked_step_and_incomplete_graph(self):
        base = {"workspace_id": "story-0123456789ab", "screenplay": {
            "screenplay_revision_id": "sp-1", "source_revision_id": "source-1", "graph_snapshot_id": "graph-1"},
            "graph": {"status": "complete", "records": []}, "setup": {"setup": saved_setup()},
            "step": "character_images", "run_id": "run-1"}
        setup = saved_setup()
        setup["automate_steps"]["character_images"] = False
        with self.assertRaisesRegex(ValueError, "checked"):
            build_entity_image_batches(**{**base, "setup": {"setup": setup}})
        with self.assertRaisesRegex(ValueError, "complete graph"):
            build_entity_image_batches(**{**base, "graph": {"status": "building", "records": []}})

    @patch("story_builder.services.storyboard.FFLF_AUTOMATION_ENABLED", True)
    def test_checked_frame_stage_builds_deterministic_first_last_batches_and_respects_skips(self):
        setup = saved_setup()
        setup["automate_steps"]["frame_images"] = True
        setup["image_stage_settings"]["frame_images"] = dict(setup["image_stage_settings"]["character_images"])
        screenplay = {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
            "graph_snapshot_id": "graph-1", "screenplay": {"scenes": [{"scene_number": 1,
                "slugline": "INT. STATION - NIGHT", "summary": "Mira enters.", "shots": [
                    {"shot_number": 1, "action": "Mira steps onto the platform.", "direction": {
                        "camera": "Slow push", "lighting": "Cold practicals", "mood": "Uneasy",
                        "sfx": "Distant train brakes", "music": "Low cello pulse"}},
                    {"shot_number": 2, "action": "The train breaks through fog."}]}]}}
        clip = story_clip_id("story-1", "sp-1", 1, 1)
        args = {"workspace_id": "story-1", "screenplay": screenplay, "setup": {"setup": setup},
            "run_id": "run-1", "skipped_shots": {(1, 2)}, "selected_frames": {("first_frame", clip)}}
        batches = build_clip_frame_image_batches(**args)
        self.assertEqual([batch["asset_role"] for batch in batches], ["last_frame"])
        self.assertEqual(len(batches[0]["candidates"]), 1)
        lineage = batches[0]["settings"]["lineage"]
        self.assertEqual(lineage["clip_id"], clip)
        self.assertIn("Mira steps onto the platform", batches[0]["prompt"])
        self.assertIn("Slow push", batches[0]["prompt"])
        self.assertIn("Cold practicals", batches[0]["prompt"])
        self.assertIn("Distant train brakes", batches[0]["prompt"])
        self.assertTrue(batches[0]["settings"]["director_review_required"])
        self.assertEqual(batches, build_clip_frame_image_batches(**args))
        selected_style = {"directing_style": {"style_id": "noir", "display_name": "Noir",
            "style_version_id": "noir:v1", "version": 1, "guidance": "Deep shadow."}}
        styled = build_clip_frame_image_batches(**{**args, "style_selection": selected_style})
        self.assertIn("Deep shadow", styled[0]["prompt"])
        self.assertNotEqual(batches[0]["idempotency_key"], styled[0]["idempotency_key"])
        oversized = {**screenplay, "screenplay": {"scenes": [{"scene_number": 1, "shots": [
            {"shot_number": 1, "action": "x" * 7000}]}]}}
        with self.assertRaisesRegex(ValueError, "exceeds the 6,999-character image limit"):
            build_clip_frame_image_batches(**{**args, "screenplay": oversized, "selected_frames": set()})

    @patch("story_builder.services.storyboard.FFLF_AUTOMATION_ENABLED", True)
    def test_qwen_frame_batches_attach_only_selected_images_for_screenplay_cited_entities(self):
        setup = saved_setup()
        setup["automate_steps"]["frame_images"] = True
        setup["image_stage_settings"]["frame_images"] = {"workflow_id": "qwen_image_edit_2511",
            "width": 1280, "height": 720, "steps": 8, "cfg": 1.0}
        clip = story_clip_id("story-1", "sp-1", 1, 1)
        screenplay = {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
            "graph_snapshot_id": "graph-1", "screenplay": {"scenes": [{"scene_number": 1,
                "slugline": "INT. STATION", "shots": [{"shot_number": 1, "action": "Mira enters.",
                    "evidence_record_ids": ["event-1", "char-mira", "char-other"]}]}]}}
        graph = {"status": "complete", "records": [
            {"record_id": "event-1", "kind": "event", "type": "action", "name": "Mira enters"},
            {"record_id": "char-mira", "kind": "entity", "type": "character", "name": "Mira"},
            {"record_id": "char-other", "kind": "entity", "type": "character", "name": "Other"},
            {"record_id": "unmentioned", "kind": "entity", "type": "character", "name": "Unmentioned"}]}
        opening = {"asset_id": "frame-open", "sha256": "a" * 64}
        mira = {"asset_id": "mira-image", "sha256": "b" * 64}
        batches = build_clip_frame_image_batches(workspace_id="story-1", screenplay=screenplay,
            setup={"setup": setup}, run_id="run-1", graph=graph,
            selected_entity_images={"char-mira": mira, "char-other": {"asset_id": "other-image", "sha256": "c" * 64},
                "unmentioned": {"asset_id": "unmentioned-image", "sha256": "d" * 64}},
            selected_frame_images={("first_frame", clip): opening})
        first, last = batches
        other = {"asset_id": "other-image", "sha256": "c" * 64}
        self.assertEqual(first["settings"]["image_references"], [mira, other])
        self.assertEqual(last["settings"]["image_references"], [opening, mira, other])
        self.assertEqual(last["settings"]["lineage"]["referenced_entity_ids"], ["char-mira", "char-other"])
        self.assertNotIn("unmentioned-image", json.dumps(last["settings"]["image_references"]))
        self.assertIn("Reference 1: opening frame", last["prompt"])

    @patch("story_builder.services.storyboard.FFLF_AUTOMATION_ENABLED", True)
    def test_qwen_automated_frames_fail_with_clear_error_when_no_cited_image_is_selected(self):
        setup = saved_setup()
        setup["automate_steps"]["frame_images"] = True
        setup["image_stage_settings"]["frame_images"] = {"workflow_id": "qwen_image_edit_2511",
            "width": 1280, "height": 720, "steps": 8, "cfg": 1.0}
        screenplay = {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
            "graph_snapshot_id": "graph-1", "screenplay": {"scenes": [{"scene_number": 1,
                "slugline": "INT. STATION", "shots": [{"shot_number": 1, "action": "Train arrives."}]}]}}
        with self.assertRaisesRegex(ValueError, "needs at least one selected character, location, or opening-frame image"):
            build_clip_frame_image_batches(workspace_id="story-1", screenplay=screenplay,
                setup={"setup": setup}, run_id="run-1")

    def test_worker_selects_frame_roles_independently_by_clip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            selection = ProductionImageSelection(root / "selection.sqlite3")
            workspace, revision = "story-1", "sp-1"
            setup = saved_setup()
            setup["automate_steps"]["frame_images"] = True
            setup["image_stage_settings"]["frame_images"] = dict(setup["image_stage_settings"]["character_images"])
            digest = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            accept = _director_acceptor(root=root, story=FakeStory(), selections=selection,
                setup_service=FakeSetup(setup))
            clip = story_clip_id(workspace, revision, 1, 1)
            with patch("story_builder.isolated_image_worker.assign_media_role") as assign:
                for role in ("first_frame", "last_frame"):
                    job = {"project_id": workspace, "job_id": f"job-{role}",
                        "output_asset_id": f"asset-{role}", "asset_role": role,
                        "settings": {"stage": "frame_images", "setup_sha256": digest,
                            "workflow_id": "z_image_turbo", "width": 1280, "height": 720,
                            "steps": 8, "cfg": 1.0, "lineage": {
                                "screenplay_revision_id": revision, "source_revision_id": "source-1",
                                "graph_snapshot_id": "graph-1", "style_selection_snapshot_id": None,
                                "target_type": "clip", "clip_id": clip, "scene_number": 1, "shot_number": 1}}}
                    accept(job)
                    self.assertIsNotNone(selection.get(project_id=workspace, screenplay_revision_id=revision,
                        target_type=role, target_record_id=clip))
            self.assertEqual(assign.call_count, 2)

    def test_worker_accepts_only_current_checked_setup_and_assigns_role_before_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            selection = ProductionImageSelection(Path(temporary) / "selection.sqlite3")
            setup = saved_setup()
            digest = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            job = {"project_id": "story-0123456789ab", "job_id": "job-1", "output_asset_id": "pa-0123456789abcdef",
                "asset_role": "character_master", "settings": {"stage": "character_images", "setup_sha256": digest,
                    "workflow_id": "z_image_turbo", "width": 1280, "height": 720, "steps": 8, "cfg": 1.0,
                    "lineage": {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
                        "graph_snapshot_id": "graph-1", "target_type": "character", "target_record_id": "char-1"}}}
            calls = []
            accept = _director_acceptor(root=Path(temporary), story=FakeStory(), selections=selection,
                setup_service=FakeSetup(setup))
            with patch("story_builder.isolated_image_worker.assign_media_role", side_effect=lambda *args: calls.append("role")):
                accept(job)
            calls.append("selected" if selection.get(project_id=job["project_id"], screenplay_revision_id="sp-1",
                target_type="character", target_record_id="char-1") else "missing")
            self.assertEqual(calls, ["role", "selected"])
            with self.assertRaisesRegex(ValueError, "stage changed"):
                _director_acceptor(root=Path(temporary), story=FakeStory(), selections=selection,
                    setup_service=FakeSetup({**setup, "automate_steps": {**setup["automate_steps"], "character_images": False}}))(job)

    def test_worker_rejects_old_or_changed_screenplay_before_selecting(self):
        with tempfile.TemporaryDirectory() as temporary:
            selection = ProductionImageSelection(Path(temporary) / "selection.sqlite3")
            setup = saved_setup()
            digest = hashlib.sha256(json.dumps(setup, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            job = {"project_id": "story-0123456789ab", "job_id": "job-1", "output_asset_id": "pa-0123456789abcdef",
                "asset_role": "character_master", "settings": {"stage": "character_images", "setup_sha256": digest,
                    "workflow_id": "z_image_turbo", "width": 1280, "height": 720, "steps": 8, "cfg": 1.0,
                    "lineage": {"screenplay_revision_id": "sp-1", "source_revision_id": "source-1",
                        "graph_snapshot_id": "graph-1", "target_type": "character", "target_record_id": "char-1"}}}
            with self.assertRaisesRegex(ValueError, "no longer current"):
                _director_acceptor(root=Path(temporary), story=FakeStory(accepted=False), selections=selection,
                    setup_service=FakeSetup(setup))(job)
            self.assertIsNone(selection.get(project_id=job["project_id"], screenplay_revision_id="sp-1",
                target_type="character", target_record_id="char-1"))

    def test_stale_automated_image_fails_before_gpu_or_provider_calls(self):
        from story_builder.services.production_image_workflows import compile_image_candidates
        from story_builder.services.production_image_worker import ProductionImageWorker
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = ProductionImageJobStore(root / "jobs.sqlite3")
            compiled = compile_image_candidates(workflow_id="z_image_turbo", prompt="Ada portrait",
                control_mode="assisted_manual", seed=7, output_prefix="story/character_master")
            store.enqueue_batch(project_id="story-0123456789ab", run_id="run-1", idempotency_key="stale",
                workflow_id=compiled["workflow_id"], workflow_version=compiled["workflow_version"],
                asset_role="character_master", prompt=compiled["prompt"],
                settings={"director_review_required": True, "director_provider": "codex"},
                candidates=compiled["candidates"][:1])
            worker = ProductionImageWorker(store, comfy_url="http://127.0.0.1:9", output_root=root / "assets",
                register_output=lambda **_: {}, validate_candidate=lambda _job: "Screenplay changed.",
                director_provider_preflight=lambda _provider: self.fail("Stale work must not call the provider."),
                gpu_inspector=lambda **_: self.fail("Stale work must not reach GPU admission."))
            result = worker.process_one()
            self.assertEqual(result["status"], "failed")
            saved = store.get_job(project_id="story-0123456789ab", job_id=result["job_id"])
            self.assertEqual(saved["error"]["code"], "automated_image_inputs_stale")


if __name__ == "__main__":
    unittest.main()
