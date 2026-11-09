"""Read the existing same-origin grant boundary with a fresh browser identity.

Diagnostic, not a passing H3 security gate. Never executes a protected job.
Uses only a disposable goal/draft and removes all records on failure as well.
"""
import json
import os
import tempfile
import threading
import uuid
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

from playwright.sync_api import sync_playwright
from story_builder.isolated_server import create_app
from story_builder.services import projects
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.director_goals import Goals
from story_builder.services.director_mcp import Gateway
from story_builder.services.production_ledger import ProductionLedger


def main():
    temporary = tempfile.TemporaryDirectory(prefix='vibe-h3-browser-boundary-')
    base = Path(temporary.name)
    try:
        app = create_app(data_root=base)
        tasks = AgentTasks(base, ProductionLedger(projects.database_path(base, projects.DATABASES[0])))
        goals, owner, request = Goals(tasks), 'tool-library', str(uuid.uuid4())
        goals.create(owner, request, 'Synthetic browser authority probe: do not execute')
        goals.update(owner, request, token='test-only')
        row = Gateway(tasks, owner, request, 'test-only').call('editor_propose_session', {'name': 'never execute'})
        goals.update(owner, request, status='waiting_for_approval', token=None)
        class Quiet(WSGIRequestHandler):
            def log_message(self, *args):
                pass
        with make_server('127.0.0.1', 0, app, handler_class=Quiet) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True, executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
                    try:
                        page = browser.new_page()
                        page.goto(f'http://127.0.0.1:{server.server_port}/')
                        result = page.evaluate('''async ({task,owner}) => {
                            const path = `/api/agent/projects/${owner}/tasks/${task.task_id}/approve`;
                            const body = JSON.stringify({revision: task.revision, plan_hash: task.plan_hash});
                            const denied = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json'},body});
                            const cap = await fetch('/api/agent/computer-access').then(r=>r.json());
                            const approved = await fetch(path,{method:'POST',headers:{'Content-Type':'application/json',
                                'X-Vibe-Computer-Token':cap.session_token},body});
                            return {without_grant:denied.status, grant_obtainable:!!cap.session_token,
                                with_self_fetched_grant:approved.status};
                        }''', {'task': row, 'owner': owner})
                        assert result['without_grant'] == 400, result
                        assert result['grant_obtainable'] and result['with_self_fetched_grant'] == 200, result
                        saved = tasks.get(owner, row['task_id'])
                        assert saved['status'] == 'approved' and saved['invocation'] is None
                        print(json.dumps({'H3_security_gate': 'BLOCKED', 'fresh_browser_identity': True,
                            **result, 'protected_execution': False,
                            'reason': 'Existing local grant discovery does not distinguish owner from same-origin browser automation.'}), flush=True)
                    finally:
                        browser.close()
            finally:
                server.shutdown()
                worker.join(timeout=5)
                assert not worker.is_alive()
    finally:
        temporary.cleanup()
        assert not base.exists()
        print('CLEANUP verified: disposable proposal/approval only; no jobs or owner data', flush=True)


if __name__ == '__main__':
    main()
