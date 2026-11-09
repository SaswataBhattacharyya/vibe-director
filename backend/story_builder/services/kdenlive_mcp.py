"""Supervise the private SDK client; no model-authored commands or paths."""
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[3]
RUNTIME = APP / 'local_data/runtimes/kdenlive-mcp'
REVISION = 'b1ff6d5d0263c9074230b9a5d02a6a5d58d2386e'


def capability():
    try:
        pinned = json.loads((RUNTIME / 'vibe-runtime.json').read_text()).get('revision') == REVISION
    except (OSError, ValueError):
        pinned = False
    checks = {'pinned_runtime': pinned and (RUNTIME / 'apps/mcp-server/dist/cli.js').is_file(),
              **{name: bool(shutil.which(name)) for name in ('node', 'melt', 'ffmpeg', 'ffprobe')}}
    return {'ready': all(checks.values()), 'checks': checks, 'revision': REVISION,
            'message': 'CPU MCP join adapter; runtime services are checked at execution.' if all(checks.values())
                       else 'Install the pinned Kdenlive MCP runtime and host melt/FFmpeg before preparing joins.'}


def run(folder, operation, progress):
    if operation not in {'prepare', 'render'} or not capability()['ready']:
        raise ValueError('Kdenlive MCP runtime is unavailable or the operation is invalid.')
    folder = Path(folder).resolve()
    with (folder / f'{operation}.log').open('ab') as log, (folder / f'{operation}.result').open('w+') as result:
        process = subprocess.Popen([shutil.which('node'), str(Path(__file__).with_name('kdenlive_mcp_client.mjs')),
            str(RUNTIME), str(folder), operation], stdout=result, stderr=log, text=True,
            start_new_session=True, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                'MELT_PATH': shutil.which('melt'), 'FFMPEG_PATH': shutil.which('ffmpeg'), 'FFPROBE_PATH': shutil.which('ffprobe')})
        began = time.monotonic()
        try:
            while process.poll() is None:
                if time.monotonic()-began > 3700:
                    raise ValueError('Kdenlive MCP operation exceeded its execution limit.')
                progress('kdenlive', 'Kdenlive MCP is preparing the join.' if operation == 'prepare' else 'Kdenlive MCP is rendering the approved join.', 50)
                time.sleep(.5)
            result.seek(0)
            output = result.read(1024*1024)
            if process.returncode:
                raise ValueError('Kdenlive MCP failed: ' + (folder / f'{operation}.log').read_text(errors='replace')[-3000:])
            return json.loads(output)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()

