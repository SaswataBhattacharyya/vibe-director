"""H1-only stdio MCP: fixed disposable project; no general execution endpoint.

Read operations use the owner's explicitly authorized test-read policy. Drafts
stay unapproved in the existing task ledger. Never import this as an app server.
"""
import json
import sys
import time
from pathlib import Path

from jsonschema import validate
from story_builder.isolated_server import create_app
from story_builder.services import agent_workspace_tools as workspace
from story_builder.services import media_library, projects, video_repertoire
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.production_ledger import ProductionLedger


class Gateway:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if not (self.root.parent / 'H1_TEST_ONLY').is_file():
            raise ValueError('Disposable probe marker required')
        create_app(data_root=self.root)
        self.owner = 'tool-library'
        self.tasks = AgentTasks(self.root, ProductionLedger(projects.database_path(self.root, projects.DATABASES[0])))
        self.tools = [
            {'name': 'media_list', 'description': 'Read media in the fixed test project. Use returned IDs for inspection.',
             'inputSchema': workspace.schema('media.list')},
            {'name': 'media_inspect', 'description': 'Inspect one owned media ID returned by media_list.',
             'inputSchema': {'type': 'object', 'additionalProperties': False,
                             'required': ['asset_id'], 'properties': {'asset_id': {'type': 'string'}}}},
            {'name': 'editor_propose_session', 'description': 'Propose an Editor session. Always waits for human approval; does not create or run it.',
             'inputSchema': workspace.schema('editor.create_session')},
        ]
        for tool in self.tools:
            tool['annotations'] = {'readOnlyHint': tool['name'] != 'editor_propose_session',
                                   'destructiveHint': False, 'openWorldHint': False}

    def call(self, name, arguments):
        schema = next((t['inputSchema'] for t in self.tools if t['name'] == name), None)
        if schema is None:
            raise ValueError('Tool is not allowlisted')
        validate(arguments, schema)
        tool = {'media_list': 'media.list', 'media_inspect': 'media.inspect',
                'editor_propose_session': 'editor.create_session'}[name]
        assets = [arguments['asset_id']] if name == 'media_inspect' else []
        settings = {} if assets else arguments
        # Host-owned interruption gate; never an agent-controlled path/duration.
        if name == 'media_inspect' and (self.root.parent / 'hold-inspect').exists():
            time.sleep(15)
        task = self.tasks.propose(self.owner, {'tool_id': tool, 'asset_ids': assets, 'settings': settings})
        if name == 'editor_propose_session':
            return {'task_id': task['task_id'], 'status': 'waiting_for_approval',
                    'revision': task['current_revision'], 'plan_hash': task['plan_hash']}
        # Test-host read policy only. This branch cannot execute a draft/write tool.
        approval = {'revision': task['current_revision'], 'plan_hash': task['plan_hash']}
        self.tasks.approve(self.owner, task['task_id'], approval)
        task = self.tasks.run(self.owner, task['task_id'], approval)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            task = self.tasks.poll(self.owner, task['task_id'])
            if task['status'] in {'completed', 'failed', 'cancelled', 'recovery_required'}:
                break
            time.sleep(.1)
        if task['status'] != 'completed':
            raise RuntimeError('Read job did not complete: ' + task['status'])
        job = video_repertoire.read_job(workspace.KIND, task['invocation']['job_id'])
        result = job['result']['result']
        if name == 'media_list':
            result = {'assets': [{k: a.get(k) for k in ('asset_id', 'filename', 'mime', 'sha256')}
                                 for a in result['assets']]}
        return {'task_id': task['task_id'], 'result': result}


def serve(root):
    gateway = Gateway(root)
    for line in sys.stdin:
        request = json.loads(line)
        if 'id' not in request:
            continue
        try:
            method = request['method']
            if method == 'initialize':
                result = {'protocolVersion': request['params']['protocolVersion'], 'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'vibe-h1-disposable', 'version': '1'}}
            elif method == 'ping':
                result = {}
            elif method == 'tools/list':
                result = {'tools': gateway.tools}
            elif method == 'tools/call':
                try:
                    params = request['params']
                    value = gateway.call(params['name'], params.get('arguments', {}))
                    result = {'content': [{'type': 'text', 'text': json.dumps(value)}], 'isError': False}
                except Exception as exc:
                    result = {'content': [{'type': 'text', 'text': str(exc)[:500]}], 'isError': True}
            else:
                raise ValueError('Unsupported MCP method')
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except Exception as exc:
            response = {'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32601, 'message': str(exc)[:500]}}
        print(json.dumps(response), flush=True)


if __name__ == '__main__':
    serve(sys.argv[1])
