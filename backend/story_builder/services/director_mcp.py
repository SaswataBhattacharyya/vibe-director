"""Typed H2 gateway. The host binds project/goal; model arguments cannot grant access."""
import json
import sys
import time
from pathlib import Path

from jsonschema import validate

from . import agent_workspace_tools as workspace, video_repertoire
from .director_goals import Goals
from .production_ledger import LedgerConflict, stable_hash


class Gateway:
    def __init__(self, tasks, owner, request, token):
        self.tasks, self.owner, self.request, self.token = tasks, owner, request, token
        self.goals = Goals(tasks)
        single = lambda key: {'type': 'object', 'additionalProperties': False, 'required': [key],
                             'properties': {key: {'type': 'string', 'minLength': 1, 'maxLength': 100}}}
        self.tools = [
            {'name': 'media_list', 'description': 'Discover owned media. Use returned IDs for inspection.',
             'inputSchema': workspace.schema('media.list')},
            {'name': 'media_inspect', 'description': 'Measure one owned source on CPU; returns duration, streams and source hash.',
             'inputSchema': single('asset_id')},
            {'name': 'task_status', 'description': 'Observe one existing task in this goal; never dispatches it.',
             'inputSchema': single('task_id')},
            {'name': 'editor_propose_session', 'description': 'Prepare a draft Editor task only. Human approval is required; never creates or runs a session.',
             'inputSchema': workspace.schema('editor.create_session')},
            {'name': 'editor_propose_selection', 'description': 'Draft ordered source ranges on an existing Editor session. Requires separate human approval and execution; never renders.',
             'inputSchema': workspace.schema('editor.select_media')},
            {'name': 'goal_pause', 'description': 'Record a missing-information question or runtime blocker. Cannot mark a goal complete or authorize tools.',
             'inputSchema': {'type': 'object', 'additionalProperties': False, 'required': ['reason', 'message'],
                 'properties': {'reason': {'enum': ['clarification_needed', 'runtime_blocked']},
                                'message': {'type': 'string', 'minLength': 1, 'maxLength': 2000}}}},
        ]
        for tool in self.tools:
            tool['annotations'] = {'readOnlyHint': tool['name'] not in {'editor_propose_session', 'editor_propose_selection', 'goal_pause'},
                                   'destructiveHint': False, 'openWorldHint': False}

    def authorized(self):
        goal = self.goals.get(self.owner, self.request)
        if goal['status'] != 'running' or goal['state'].get('token') != self.token:
            raise LedgerConflict('Goal permission expired or was cancelled.')
        return goal

    def call(self, name, arguments):
        goal = self.authorized()
        schema = next((t['inputSchema'] for t in self.tools if t['name'] == name), None)
        if schema is None:
            raise ValueError('Tool is not permitted by the H2 gateway.')
        validate(arguments, schema)
        if name == 'goal_pause':
            self.goals.update(self.owner, self.request, requested_stop=arguments)
            return {'recorded': True, 'goal_complete': False}
        if name == 'task_status':
            if arguments['task_id'] not in {s['task_id'] for s in goal['steps']}:
                raise ValueError('Task does not belong to this goal.')
            task = self.tasks.poll(self.owner, arguments['task_id'])
            from .director_goal_tasks import snapshot
            protected = snapshot(self.tasks, goal)['protected_tasks']
            return next((r for r in protected if r['task_id'] == task['task_id']),
                        {'task_id': task['task_id'], 'status': task['status'], 'plan_hash': task['plan_hash']})
        tool = {'media_list': 'media.list', 'media_inspect': 'media.inspect',
                'editor_propose_session': 'editor.create_session', 'editor_propose_selection': 'editor.select_media'}[name]
        # Existing adapters validate exact schemas, input ownership, hashes and
        # frozen snapshots. Only these two reads have host execution permission.
        if name == 'media_inspect':
            from shutil import which
            if not which('ffprobe'):
                raise RuntimeError('ffprobe is unavailable; media inspection is blocked.')
            from .agent_editor import EXTENSIONS
            self.tasks._assets(self.owner, [arguments['asset_id']], extensions=EXTENSIONS)
        step, fresh = self.goals.step(self.owner, self.request, name, arguments)
        if step['result'] is not None:
            return step['result']
        if not fresh and step['task_id'] is None:
            raise LedgerConflict('Unacknowledged tool preparation; reconcile before retrying. It was not repeated.')
        if fresh:
            task = self.tasks.propose(self.owner, {'tool_id': tool,
                'asset_ids': [arguments['asset_id']] if name == 'media_inspect' else
                    list(dict.fromkeys(s['asset_id'] for s in arguments['selection'])) if name == 'editor_propose_selection' else [],
                'settings': {} if name == 'media_inspect' else arguments})
            self.goals.receipt(self.owner, self.request, step['step_key'], task_id=task['task_id'])
        else:
            task = self.tasks.get(self.owner, step['task_id'])
        self.authorized()
        if task['plan']['tool_id'] != tool or task['current_revision'] != 1:
            raise LedgerConflict('Gateway task was revised or substituted. Host read authority cannot approve it.')
        if name in {'editor_propose_session', 'editor_propose_selection'}:
            result = {'task_id': task['task_id'], 'status': 'waiting_for_approval',
                      'revision': task['current_revision'], 'plan_hash': task['plan_hash']}
        else:
            approval = {'revision': task['current_revision'], 'plan_hash': task['plan_hash']}
            if task['status'] == 'draft':
                with self.tasks.ledger._connect() as db:
                    self.tasks._event(db, self.owner, task['task_id'], 'host_read_policy',
                                      {'goal_id': self.request, 'tool': tool, 'policy': 'H2 explicit project opt-in'})
                self.tasks.approve(self.owner, task['task_id'], approval)
            self.authorized()
            # run() reconciles the existing invocation; never replaces a lost job.
            task = self.tasks.run(self.owner, task['task_id'], approval)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                self.authorized()
                task = self.tasks.poll(self.owner, task['task_id'])
                if task['status'] in {'completed', 'failed', 'cancelled', 'recovery_required'}:
                    break
                time.sleep(.1)
            if task['status'] != 'completed':
                raise RuntimeError('Read task requires observation/recovery: ' + task['status'])
            job = video_repertoire.read_job(workspace.KIND, task['invocation']['job_id'])
            value = job['result']['result']
            if name == 'media_list':
                value = {key: value.get(key) for key in ('total', 'offset', 'limit')}
                raw = job['result']['result']['assets']
                value['assets'] = [{k: a.get(k) for k in ('asset_id', 'filename', 'mime', 'sha256')} for a in raw]
            else:
                value = {'sources': [{k: a.get(k) for k in ('asset_id', 'filename', 'mime', 'sha256', 'metadata')}
                                     for a in value['sources']]}
            result = {'task_id': task['task_id'], 'result': value}
        if len(json.dumps(result).encode()) > 16000:
            raise RuntimeError('Tool result exceeds context budget. Use a smaller discovery page.')
        result['receipt_sha256'] = stable_hash(result)
        self.goals.receipt(self.owner, self.request, step['step_key'], result=result)
        return result


def serve(manifest):
    # This path comes only from the private, host-written Codex configuration.
    from story_builder.isolated_server import create_app
    from .agent_tasks import AgentTasks
    from .production_ledger import ProductionLedger
    config = json.loads(Path(manifest).read_text())
    create_app(data_root=Path(config['root']), ledger_path=Path(config['ledger']))
    gateway = Gateway(AgentTasks(Path(config['root']), ProductionLedger(config['ledger'])),
                      config['owner'], config['request'], config['token'])
    for line in sys.stdin:
        if len(line.encode()) > 64000:
            return
        request = json.loads(line)
        if 'id' not in request:
            continue
        try:
            gateway.authorized()
            method, params = request['method'], request.get('params', {})
            if method == 'initialize':
                result = {'protocolVersion': params['protocolVersion'], 'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'vibe-director', 'version': '2'}}
            elif method == 'ping':
                result = {}
            elif method == 'tools/list':
                result = {'tools': gateway.tools}
            elif method == 'tools/call':
                try:
                    if set(params) - {'name', 'arguments', '_meta'}:
                        raise ValueError('Unsupported tool call fields.')
                    value = gateway.call(params['name'], params.get('arguments', {}))
                    result = {'content': [{'type': 'text', 'text': json.dumps(value)}], 'isError': False}
                except Exception as exc:
                    # Do not leak tracebacks, paths, credentials or raw provider errors.
                    detail = str(exc)[:350] if isinstance(exc, (LedgerConflict, RuntimeError, ValueError)) else 'Check the advertised input schema.'
                    result = {'content': [{'type': 'text', 'text': 'Tool denied or blocked: ' + detail}], 'isError': True}
            else:
                raise ValueError('Unsupported MCP method.')
            response = {'jsonrpc': '2.0', 'id': request['id'], 'result': result}
        except Exception:
            response = {'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32601, 'message': 'MCP request denied.'}}
        print(json.dumps(response), flush=True)


if __name__ == '__main__':
    serve(sys.argv[1])
