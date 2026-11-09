"""Opt-in H3 actual Codex/CPU approval continuation and browser-boundary probe.

The host represents the human reviewer through existing exact-plan APIs. This
is not evidence of a physical human click. No generation/rendering/owner data.
"""
import argparse
import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from story_builder.isolated_server import create_app
from story_builder.services import agent_access, media_library, projects
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.director_goals import Goals
from story_builder.services.production_ledger import ProductionLedger
from story_builder.tests.harness_probe import fixture, cleanup_jobs
from story_builder.tests.harness_production_acceptance import call, wait


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--live-account', action='store_true')
    args = parser.parse_args()
    if not args.live_account:
        parser.error('--live-account required')
    temp = tempfile.TemporaryDirectory(prefix='vibe-h3-approval-')
    base, controllers, record = Path(temp.name), [], None
    try:
        record = fixture(base)
        owner, request = 'tool-library', str(uuid.uuid4())
        with patch.dict(os.environ, VIBE_DIRECTOR_HARNESS='codex', VIBE_DIRECTOR_HARNESS_PROJECTS=owner):
            app = create_app(data_root=base / 'data')
            controllers.append(app.director_harness)
            tasks = AgentTasks(base / 'data', ProductionLedger(projects.database_path(base / 'data', projects.DATABASES[0])))
            goals = Goals(tasks)
            objective = ('Discover all project media, inspect the returned audio ID and report its duration. '
                'Then propose one Editor session named H3 approved edit. Wait for the owner to approve and separately run it. '
                'After the host resumes you with verified execution evidence, consume the new session project_id, '
                'call task_status for that completed task, then list AUDIO ONLY (kind audio, offset 0, limit 10). '
                'Report the created Editor ID and audio count. Do not propose the session twice or run/approve tasks. '
                'The full film remains unfinished; stop with an honest blocker.')
            call(app, 'POST', owner, payload={'request_id': request, 'text': objective,
                'surface': 'director', 'asset_ids': [], 'skill_refs': []})
            history, goal = wait(app, goals, owner, request)
            assert goal['status'] == 'waiting_for_approval', (goal, history)
            step = next(s for s in goal['steps'] if s['tool'] == 'editor_propose_session')
            draft = tasks.get(owner, step['task_id'])
            assert draft['status'] == 'draft' and not draft['invocation']
            saved_thread = goal['thread_id']
            print(json.dumps({'initial_proposal': 'PASS', 'thread': saved_thread, 'task': draft['task_id'],
                              'status': goal['status']}), flush=True)
            # Existing exact-plan human route; token remains only in trusted host.
            exact = {'revision': draft['current_revision'], 'plan_hash': draft['plan_hash']}
            def human(action):
                return call(app, 'POST', owner, f'tasks/{draft["task_id"]}/{action}', exact, grant=agent_access._TOKEN)
            assert human('approve')['status'] == 'approved'
            history, approved = wait(app, goals, owner, request)
            assert approved['status'] == 'waiting_for_execution', approved
            assert tasks.get(owner, draft['task_id'])['invocation'] is None
            # Persist approval across app recreation before the separate run action.
            app = create_app(data_root=base / 'data')
            controllers.append(app.director_harness)
            assert human('run')['invocation']
            history, resumed = wait(app, goals, owner, request)
            assert resumed['thread_id'] == saved_thread
            assert len(history['messages']) == 1
            task = tasks.poll(owner, draft['task_id'])
            assert task['status'] == 'completed', task
            assert resumed['state'].get('consumed_tasks', {}).get(draft['task_id']), (resumed, history)
            assert any(s['tool'] == 'media_list' and s['arguments'].get('kind') == 'audio' for s in resumed['steps']), (resumed, history)
            result = json.loads(task['report'])['result']['result']
            assert result['project_id'] in history['messages'][0]['reply'], history
            before = task['invocation']
            assert human('run')['invocation'] == before
            print(json.dumps({'automatic_approval_continuation': 'PASS', 'thread': saved_thread,
                'user_messages': 1, 'created_editor': result['project_id'], 'invocation': before,
                'consumed_result': resumed['state']['consumed_tasks'],
                'steps': [s['tool'] for s in resumed['steps']], 'reply': history['messages'][0]['reply']}), flush=True)
            # Verify actual thread history has just one original user message.
            from story_builder.services.director_codex_bridge import AppServer
            from story_builder.services.director_codex_config import configure
            import shutil
            runtime = app.director_harness.base(owner)
            configure(runtime, shutil.which('codex'), {'root': str(base / 'data'), 'ledger': str(tasks.ledger.path),
                'owner': owner, 'request': request, 'token': 'revoked-no-tools'}, Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))))
            server = None
            try:
                server = AppServer(runtime, shutil.which('codex'))
                data = server.request('thread/read', {'threadId': saved_thread, 'includeTurns': True})
                count = json.dumps(data).count('"type": "userMessage"')
                assert count == 1, count
                print('ACTUAL THREAD one userMessage; resumed host context, no new chat', flush=True)
            finally:
                if server:
                    server.close()
                (runtime / 'codex/auth.json').unlink(missing_ok=True)
        assert projects.digest(media_library.asset_path(base / 'data', owner, record['asset_id'])[0]) == record['sha256']
    finally:
        try:
            for controller in controllers:
                for owner, request in list(controller.workers):
                    controller.interrupt(owner, request)
                for worker in list(controller.workers.values()):
                    worker.join(timeout=10)
                assert not controller.workers
            cleanup_jobs(base)
        finally:
            temp.cleanup()
            assert not base.exists()
            print('CLEANUP verified: synthetic media, jobs, records, credentials and threads removed', flush=True)


if __name__ == '__main__':
    main()
