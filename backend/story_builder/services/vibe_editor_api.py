"""Small HTTP seam for editor projects; media still uses the shared library API."""
import re
from . import vibe_editor as editor
from . import video_repertoire


def handle(root, environ, start_response, read_json, respond, *, tasks=None):
    method = environ.get('REQUEST_METHOD', 'GET').upper()
    path = environ.get('PATH_INFO', '')
    if method not in {'GET', 'POST', 'PUT'}:
        return respond(start_response, '405 Method Not Allowed', {'error': {'message': 'Unsupported method.'}})
    if method != 'GET' and environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
        raise ValueError('Use application/json.')
    body = read_json(environ) if method != 'GET' else {}
    if match := re.fullmatch(r'/api/editor/runtime/([\w.-]+)', path):
        if method != 'GET':
            raise ValueError('Preview runtime is read-only.')
        from .editor_preview import runtime_file
        content = runtime_file(match[1]).read_bytes()
        start_response('200 OK', [('Content-Type', 'application/javascript; charset=utf-8'),
                       ('X-Content-Type-Options', 'nosniff'), ('Cache-Control', 'no-cache')])
        return [content]
    if path == '/api/editor/state' and method == 'GET':
        result = editor.snapshot(root)
        from .kdenlive_mcp import capability
        result['kdenlive'] = capability()
        result['runtime'] = __import__('story_builder.services.vibe_editor_render', fromlist=['capability']).capability()
    elif path == '/api/editor/projects' and method == 'POST':
        result = editor.add_project(root, body)
    elif path == '/api/editor/styles' and method == 'POST':
        result = editor.change_style(root, body)
    elif match := re.fullmatch(r'/api/editor/styles/([\w-]+)', path):
        if method != 'PUT':
            raise ValueError('Use PUT for style changes.')
        result = editor.change_style(root, body, match[1])
    elif match := re.fullmatch(r'/api/editor/projects/([\w-]+)(?:/(command|plan|export|speech|speech-cuts|join|overlap|kdenlive-project|preview|studio|studio-action))?', path):
        project_id, operation = match.groups()
        if operation == 'join' and method == 'POST' and tasks is not None:
            from .editor_kdenlive import propose
            result = propose(root, tasks, project_id, body)
        elif operation == 'overlap' and method == 'GET' and tasks is not None:
            with editor.state(root, readonly=True) as data:
                p = editor.project(data, project_id)
                ids = [row['asset_id'] for row in p['selection']]
                revision, owner = p['revision'], p['workspace_id']
            found = []
            for row in tasks.list(owner)['tasks']:
                if row['plan']['tool_id'] == 'video.compare_clip_overlap' and [a['asset_id'] for a in row['plan']['assets']] == ids:
                    current = tasks.poll(owner, row['task_id'])
                    if current['status'] == 'completed':
                        found.append(tasks.overlap(owner, row['task_id']))
                        break
            result = {'revision': revision, 'sources': found}
        elif operation == 'kdenlive-project' and method == 'GET':
            from .editor_kdenlive import execution_folder
            from pathlib import Path
            with editor.state(root, readonly=True) as data:
                p = editor.project(data, project_id)
                output = p.get('output') or {}
                if output.get('backend') != 'kdenlive':
                    raise ValueError('Render a Kdenlive join before downloading its editable project.')
                folder = execution_folder(root, p['workspace_id'], project_id, output['execution_id']).resolve()
                path = Path(output['editable_project']).resolve()
                if not path.is_relative_to(folder) or not path.is_file():
                    raise ValueError('Editable project is unavailable.')
                content = path.read_bytes()
            start_response('200 OK', [('Content-Type', 'application/xml'), ('Content-Disposition', 'attachment; filename="editable.kdenlive"'), ('X-Content-Type-Options', 'nosniff')])
            return [content]
        elif operation in {'studio', 'studio-action'} and method == 'POST':
            from . import editor_studio
            result = (editor_studio.open_workspace if operation == 'studio' else editor_studio.operate)(root, project_id, body)
        elif operation == 'preview' and method == 'POST':
            from .editor_preview import prepare
            result = prepare(root, project_id, body)
        elif tasks is not None and ((method == 'GET' and operation == 'speech') or (method == 'POST' and operation == 'speech-cuts')):
            from . import editor_speech
            result = (editor_speech.evidence(root, tasks, project_id) if operation == 'speech'
                      else editor_speech.propose(root, tasks, project_id, body))
        elif method == 'GET' and not operation:
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
