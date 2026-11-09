"""Fresh same-origin browser attack, before/after normal human UI approval.

Default: actual HTTP/browser, mocked native rejection; no human-input claim.
--native-timeouts: real native dialogs expire unattended, never confirmed.
--human: real Approve/Run dialogs require owner input through the desktop.
Every fixture/process/job is disposable and removed even on failure.
"""
import argparse
from contextlib import contextmanager
import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from story_builder.isolated_server import create_app
from story_builder.services import agent_confirmation, projects
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.director_goals import Goals
from story_builder.services.director_mcp import Gateway
from story_builder.services.production_ledger import ProductionLedger
from story_builder.tests.harness_browser_acceptance import serve_ui


def main():
    parser = argparse.ArgumentParser(__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--native-timeouts', action='store_true')
    group.add_argument('--human', action='store_true')
    args = parser.parse_args()
    temporary = tempfile.TemporaryDirectory(prefix='vibe-h3-browser-boundary-')
    base = Path(temporary.name)
    try:
        root = base / 'data'
        app = create_app(data_root=root)
        tasks = AgentTasks(root, ProductionLedger(projects.database_path(root, projects.DATABASES[0])))
        goals, owner, request = Goals(tasks), 'tool-library', str(uuid.uuid4())
        goals.create(owner, request, 'Synthetic owner authorization check')
        goals.update(owner, request, token='test-only')
        draft = Gateway(tasks, owner, request, 'test-only').call('editor_propose_session', {'name': 'Disposable native authorization check'})
        goals.update(owner, request, status='waiting_for_approval', token=None)
        task_id = draft['task_id']
        def attack(page, action):
            result = page.evaluate('''async ({task,owner,action}) => {
                const cap = await fetch('/api/agent/computer-access').then(r=>r.json());
                const response = await fetch(`/api/agent/projects/${owner}/tasks/${task.task_id}/${action}`, {
                    method:'POST', headers:{'Content-Type':'application/json','X-Vibe-Computer-Token':cap.session_token || 'old-forged-grant'},
                    body:JSON.stringify({revision:task.revision,plan_hash:task.plan_hash})});
                return {status:response.status,cap,body:await response.json()};
            }''', {'task': draft, 'owner': owner, 'action': action})
            assert 'session_token' not in result['cap'], result
            assert result['status'] == 400, result
            return result['status']
        @contextmanager
        def denial_context():
            if args.native_timeouts or args.human:
                native = agent_confirmation._desktop_confirm
                def attack_dialog(text, action):
                    return native('TEST ATTACK — DO NOT AUTHORIZE. Expires automatically.\n\n' + text, action)
                with patch.object(agent_confirmation, 'TIMEOUT', 2), patch.object(agent_confirmation, '_desktop_confirm', side_effect=attack_dialog):
                    yield
            else:
                with patch.object(agent_confirmation, '_desktop_confirm', return_value=False):
                    yield
        with serve_ui(app) as url, sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.goto(url + '/#/editor')
                card = page.get_by_role('article', name=f'Task {task_id}')
                card.wait_for(timeout=20000)
                with denial_context():
                    assert attack(page, 'approve') == 400
                assert tasks.get(owner, task_id)['status'] == 'draft'
                if args.human:
                    print('OWNER: click checkbox and Approve in the native dialog for Disposable native authorization check.', flush=True)
                    with page.expect_response(lambda r: r.url.endswith('/approve') and r.request.method == 'POST', timeout=130000) as reply:
                        card.get_by_role('button', name='Approve this plan', exact=True).click()
                    assert reply.value.status == 200, reply.value.text()
                else:
                    # Seed ONLY the existing backend approval record, no browser credential.
                    # This is a trusted-host fixture, not claimed as human acceptance.
                    row = tasks.get(owner, task_id)
                    tasks.approve(owner, task_id, {'revision': row['current_revision'], 'plan_hash': row['plan_hash']})
                    page.reload()
                assert tasks.get(owner, task_id)['status'] == 'approved'
                assert tasks.get(owner, task_id)['invocation'] is None
                # Same browser after normal UI use AND a completely fresh identity.
                with denial_context():
                    assert attack(page, 'run') == 400
                    fresh = browser.new_context()
                    try:
                        other = fresh.new_page()
                        other.goto(url + '/#/editor')
                        assert attack(other, 'approve') == 400
                        assert attack(other, 'run') == 400
                    finally:
                        fresh.close()
                assert tasks.get(owner, task_id)['invocation'] is None
                if args.human:
                    print('OWNER: click checkbox and Run in the separate native dialog. CPU session creation only.', flush=True)
                    with page.expect_response(lambda r: r.url.endswith('/run') and r.request.method == 'POST', timeout=130000) as reply:
                        card.get_by_role('button', name='Run approved task', exact=True).click()
                    assert reply.value.status == 200, reply.value.text()
                    import time
                    until = time.monotonic() + 15
                    while time.monotonic() < until:
                        saved = tasks.poll(owner, task_id)
                        if saved['status'] == 'completed': break
                        time.sleep(.1)
                    assert saved['status'] == 'completed', saved
                    print(json.dumps({'human_native_approve_and_run': 'PASS', 'job': saved['invocation'],
                        'completed_CPU_session': True}), flush=True)
                print(json.dumps({'browser_cannot_independently_approve_or_run': 'PASS',
                    'fresh_identity_and_after_UI': True, 'reusable_browser_credential': False,
                    'native_input': 'actual-human' if args.human else 'actual-expiry' if args.native_timeouts else 'mocked-denial'}), flush=True)
            finally:
                browser.close()
    finally:
        from story_builder.tests.harness_probe import cleanup_jobs
        cleanup_jobs(base)
        temporary.cleanup()
        assert not base.exists()
        print('CLEANUP verified: isolated browser, CPU task/session, approvals and jobs removed; owner data untouched', flush=True)


if __name__ == '__main__':
    main()
