"""Actual shared chat UI, isolated backend and real Codex. Imported only opt-in."""
import os
from contextlib import contextmanager
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from urllib.request import urlopen
from wsgiref.simple_server import make_server, WSGIRequestHandler

from story_builder.isolated_server import ThreadedWSGIServer


@contextmanager
def serve_ui(app):
    class Quiet(WSGIRequestHandler):
        def log_message(self, *args):
            pass
    frontend = Path(__file__).resolve().parents[3] / 'frontend'
    with make_server('127.0.0.1', 0, app, server_class=ThreadedWSGIServer, handler_class=Quiet) as server:
        serving = threading.Thread(target=server.serve_forever, daemon=True)
        serving.start()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        env = {**os.environ, 'VIBE_DIRECTOR_API_PROXY': f'http://127.0.0.1:{server.server_port}'}
        vite = subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1',
            '--port', str(port), '--strictPort', '--configLoader', 'runner'], cwd=frontend, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            url = f'http://127.0.0.1:{port}'
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    with urlopen(url, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise TimeoutError('Test-owned frontend did not start.')
            yield url
        finally:
            try:
                os.killpg(vite.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            vite.wait(timeout=10)
            server.shutdown()
            serving.join(timeout=5)
            assert not serving.is_alive()


def submit(app, objective):
    from playwright.sync_api import sync_playwright
    with serve_ui(app) as url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True,
                executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'))
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                errors, writes = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda req: writes.append(req.url) if req.method != 'GET' and '/api/editor/projects' in req.url else None)
                with page.expect_response(lambda response: '/conversation' in response.url and response.request.method == 'GET'):
                    page.goto(url + '/#/editor')
                page.get_by_label('Message the project Director', exact=True).fill(objective)
                page.get_by_role('button', name='Send to project Director', exact=True).click()
                goal = page.get_by_role('region', name='Saved Director goal')
                goal.get_by_text('waiting for approval', exact=False).wait_for(timeout=170000)
                log = page.get_by_role('log', name='Director conversation history')
                assert '0.3' in log.inner_text()
                assert not errors, errors
                assert not writes, 'Chat created or modified an Editor session before approval'
                page.goto(url + '/#/video')
                page.get_by_role('region', name='Saved Director goal').wait_for()
                assert 'waiting for approval' in page.get_by_role('region', name='Saved Director goal').inner_text()
                print('BROWSER actual Editor composer → real Codex tools → waiting approval; same goal visible in Director; no Editor writes', flush=True)
            finally:
                browser.close()
