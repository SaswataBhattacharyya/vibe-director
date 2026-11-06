"""Shared discovery and explicitly approved task boundary."""
import re
from urllib.parse import parse_qs
from . import agent_access, agent_graph, agent_skills, agent_tools


def handle(root, environ, start_response, respond, *, tasks=None, conversation=None, read_json=None):
    path = environ.get('PATH_INFO', '')
    if path == '/api/agent/computer-access':
        if environ.get('REQUEST_METHOD', 'GET').upper() != 'GET' or environ.get('QUERY_STRING'):
            raise ValueError('Computer access discovery supports GET without query fields.')
        return respond(start_response, '200 OK', agent_access.capabilities(environ))
    knowledge_match = re.fullmatch(r'/api/agent/projects/([^/]+)/knowledge', path)
    if knowledge_match:
        from . import agent_knowledge
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        if environ.get('QUERY_STRING'):
            raise ValueError('Knowledge does not accept query fields.')
        if method == 'GET':
            result = agent_knowledge.read(root, tasks.ledger, knowledge_match[1])
        elif method == 'POST':
            result = agent_knowledge.save(root, tasks.ledger, knowledge_match[1], read_json(environ))
        else:
            return respond(start_response, '405 Method Not Allowed', {'error': {'code': 'method_not_allowed', 'message': 'Use GET or POST.'}})
        return respond(start_response, '200 OK', result)
    chat_match = re.fullmatch(r'/api/agent/projects/([^/]+)/conversation', path)
    if chat_match:
        if environ.get('QUERY_STRING'):
            raise ValueError('Conversation does not accept query fields.')
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        if method not in {'GET', 'POST'}:
            return respond(start_response, '405 Method Not Allowed', {'error': {'code': 'method_not_allowed', 'message': 'Use GET or POST.'}})
        result = conversation.history(chat_match[1]) if method == 'GET' else conversation.send(chat_match[1], read_json(environ))
        return respond(start_response, '200 OK', result)
    task_match = re.fullmatch(r'/api/agent/projects/([^/]+)/tasks(?:/(task-[0-9a-f]{32})(?:/(approve|run|cancel|revise))?)?', path)
    if task_match:
        if environ.get('QUERY_STRING'):
            raise ValueError('Tasks do not accept query fields.')
        owner, task, action = task_match.groups()
        agent_graph.resolve_workspace(root, owner)
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        if method == 'GET' and not action:
            result = tasks.poll(owner, task) if task else tasks.list(owner)
            rows = [result] if task else result['tasks']
            if any(row['plan']['tool_id'] == 'computer.execute' for row in rows):
                agent_access.local_request(environ)
        elif method == 'POST' and (not task or action):
            payload = read_json(environ)
            proposed = payload.get('proposal', payload) if isinstance(payload, dict) else {}
            if not isinstance(proposed, dict):
                raise ValueError('Task proposal must be an object.')
            if proposed.get('tool_id') == 'computer.execute' or (task and tasks.get(owner, task)['plan']['tool_id'] == 'computer.execute'):
                agent_access.require_grant(environ)
            if not task:
                result = tasks.propose(owner, payload)
            elif action == 'cancel':
                if payload:
                    raise ValueError('Cancel does not accept fields.')
                result = tasks.cancel(owner, task)
            else:
                result = getattr(tasks, action)(owner, task, payload)
        else:
            return respond(start_response, '405 Method Not Allowed', {'error': {'code': 'method_not_allowed', 'message': 'Unsupported task method.'}})
        return respond(start_response, '200 OK', result)
    match = re.fullmatch(r'/api/agent/projects/([^/]+)/context', path)
    if path not in {'/api/agent/tools', '/api/agent/skills'} and not match:
        return respond(start_response, '404 Not Found', {'error': {'code': 'not_found', 'message': 'Agent endpoint not found.'}})
    if environ.get('REQUEST_METHOD', 'GET').upper() != 'GET':
        return respond(start_response, '405 Method Not Allowed', {'error': {'code': 'method_not_allowed', 'message': 'Discovery supports GET only.'}})
    query = parse_qs(environ.get('QUERY_STRING', ''), keep_blank_values=True, strict_parsing=True)
    if match:
        if query:
            raise ValueError('Project context does not accept query fields.')
        workspace = match[1]
    else:
        if set(query) != {'workspace_id'} or len(query['workspace_id']) != 1:
            raise ValueError('Supply exactly one workspace_id.')
        workspace = query['workspace_id'][0]
    owner = agent_graph.resolve_workspace(root, workspace)
    result = agent_graph.context(root, owner) if match else agent_tools.tools() if path.endswith('/tools') else agent_skills.discover(root, workspace)
    return respond(start_response, '200 OK', result)
