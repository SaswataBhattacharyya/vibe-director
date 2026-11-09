"""Launch unmodified pinned Backlot against one Vibe-owned mirror, with capability auth."""
import os
import json
import uuid
import sys
from pathlib import Path

runtime, mirror, port, token = sys.argv[1:]
os.environ['OPENMONTAGE_PROJECTS_DIR'] = mirror
sys.path.insert(0, runtime)
from backlot import server  # noqa: E402
from starlette.responses import JSONResponse, RedirectResponse, HTMLResponse  # noqa: E402
import uvicorn  # noqa: E402

server.THUMB_CACHE_DIR = Path(mirror).parent / '.backlot'
app = server.create_app()
cookie = 'vibe-interface-' + token[:12]


@app.middleware('http')
async def authorize(request, call_next):
    if request.headers.get('host') not in {f'127.0.0.1:{port}', f'localhost:{port}'}:
        return JSONResponse({'error': 'Invalid host'}, status_code=400)
    if request.url.path == '/' and request.query_params.get('vibe_token') == token:
        response = RedirectResponse('/vibe', status_code=303)
        response.set_cookie(cookie, token, httponly=True, samesite='strict')
        return response
    if request.cookies.get(cookie) != token:
        return JSONResponse({'error': 'Unauthorized or read-only workspace'}, status_code=403)
    folder = Path(mirror) / 'production'
    if request.url.path == '/vibe/proposal' and request.method == 'POST':
        if request.headers.get('origin') != f'http://{request.headers.get("host")}':
            return JSONResponse({'error': 'Invalid origin'}, status_code=403)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 128 * 1024:
                return JSONResponse({'error': 'Proposal too large'}, status_code=413)
        try:
            value = json.loads(raw)
            if (not isinstance(value, dict) or set(value) != {'base_revision', 'changes'}
                    or type(value['base_revision']) is not int or not isinstance(value['changes'], list)
                    or not 1 <= len(value['changes']) <= 100):
                raise ValueError('Invalid proposal')
        except (ValueError, TypeError):
            return JSONResponse({'error': 'Invalid proposal'}, status_code=400)
        temporary = folder / f'vibe-proposal-{uuid.uuid4().hex}.tmp'
        temporary.write_text(json.dumps(value))
        temporary.replace(folder / 'vibe-proposal.json')
        return JSONResponse({'staged': True})
    if request.method not in {'GET', 'HEAD'}:
        return JSONResponse({'error': 'Native Backlot is read-only'}, status_code=403)
    if request.url.path == '/vibe':
        return HTMLResponse(Path(__file__).with_name('backlot_editor.html').read_text(), headers={'Referrer-Policy': 'no-referrer'})
    if request.url.path == '/vibe/state':
        return JSONResponse(json.loads((folder / 'vibe-state.json').read_text()))
    response = await call_next(request)
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self' http://127.0.0.1:* http://localhost:*"
    return response


uvicorn.run(app, host='127.0.0.1', port=int(port), log_level='warning')
