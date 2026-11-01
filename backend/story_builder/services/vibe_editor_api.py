"""Small HTTP seam for editor projects; media still uses the shared library API."""
import re
from . import vibe_editor as editor
from . import video_repertoire


def handle(root, environ, start_response, read_json, respond):
    method = environ.get('REQUEST_METHOD', 'GET').upper()
    path = environ.get('PATH_INFO', '')
    if method not in {'GET', 'POST', 'PUT'}:
        return respond(start_response, '405 Method Not Allowed', {'error': {'message': 'Unsupported method.'}})
    if method != 'GET' and environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
        raise ValueError('Use application/json.')
    body = read_json(environ) if method != 'GET' else {}
    if path == '/api/editor/state' and method == 'GET':
        result = editor.snapshot(root)
        result['runtime'] = __import__('story_builder.services.vibe_editor_render', fromlist=['capability']).capability()
    elif path == '/api/editor/projects' and method == 'POST':
        result = editor.add_project(root, body)
    elif path == '/api/editor/styles' and method == 'POST':
        result = editor.change_style(root, body)
    elif match := re.fullmatch(r'/api/editor/styles/([\w-]+)', path):
        if method != 'PUT':
            raise ValueError('Use PUT for style changes.')
        result = editor.change_style(root, body, match[1])
    elif match := re.fullmatch(r'/api/editor/projects/([\w-]+)(?:/(command|plan|export))?', path):
        project_id, operation = match.groups()
        if method == 'GET' and not operation:
            result = next((p for p in editor.snapshot(root)['projects'] if p['id'] == project_id), None)
            if result is None:
                raise ValueError('Project not found.')
            if result.get('job_id'):
                result['job'] = editor.saved_job(result)
        elif method == 'PUT' and not operation:
            result = editor.update_project(root, project_id, body)
        elif method == 'POST' and operation in {'command', 'plan', 'export'}:
            result = {'command': editor.command, 'plan': editor.propose_plan, 'export': editor.export_video}[operation](root, project_id, body)
        else:
            raise ValueError('Unsupported editor operation.')
    else:
        return respond(start_response, '404 Not Found', {'error': {'message': 'Editor endpoint not found.'}})
    return respond(start_response, '200 OK', result)
