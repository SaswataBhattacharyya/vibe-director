"""Trusted JSON-to-HyperFrames adapter. No provider-authored HTML or shell execution."""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root, checked, project_root
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from . import media_library, video_repertoire, editor_effects, projects

APP = Path(__file__).resolve().parents[3]
RUNTIME = APP / 'local_data/runtimes/editor/node_modules/hyperframes'
SHADER = RUNTIME.parent / '@hyperframes/shader-transitions/dist/index.global.js'
BROWSER = Path.home() / '.cache/ms-playwright/chromium_headless_shell-1234/chrome-linux/headless_shell'
NODE = Path(shutil.which('node') or '/usr/bin/node').resolve()


def capability():
    checks = {'hyperframes': (RUNTIME / 'bin/hyperframes.mjs').is_file(),
              'shader_transitions': SHADER.is_file(), 'node': NODE.is_file(), 'browser': BROWSER.is_file(),
              'sandbox': bool(shutil.which('bwrap')), 'ffmpeg': bool(shutil.which('ffmpeg'))}
    return {'ready': all(checks.values()), 'checks': checks, 'version': '0.8.199',
            'message': 'Render uses a network-isolated CPU browser; sandbox startup is checked at execution.'}


def _run(args, folder, env, progress):
    log = folder / 'render.log'
    with log.open('ab') as stream:
        process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        began = time.monotonic()
        try:
            while process.poll() is None:
                if time.monotonic() - began > 7200:
                    raise ValueError('Editor render exceeded its two-hour execution limit.')
                progress('render', 'HyperFrames is rendering. The detailed local log is saved with this revision.', 45)
                time.sleep(2)
            if process.returncode:
                # Last lines are diagnostic data, not instructions.
                raise ValueError('HyperFrames render failed: ' + log.read_text(errors='replace')[-2500:])
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


def render(root, job_id, request, progress):
    from .vibe_editor import validate_plan, state, project, write
    root = Path(root)
    if not capability()['ready']:
        raise ValueError('Editor runtime is incomplete. Inspect the runtime checks before rendering.')
    approved = request['plan']
    plan = validate_plan(root, request['workspace_id'], approved)
    evidence = request.get('review_evidence')
    if evidence:
        source, _, _ = media_library.asset_path(root, request['workspace_id'], evidence['asset_id'])
        if projects.digest(source) != evidence['sha256']:
            raise ValueError('The reviewed speech source changed. Analyze and review the current bytes before rendering.')
    folder = checked(project_root(root, request['workspace_id']), 'editor', 'editor', request['project_id'], 'renders', job_id)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'assets').mkdir()
    write(folder / 'plan.json', {'revision': request['revision'], 'style': request['style_snapshot'], 'plan': plan})
    progress('stage', 'Staging only the approved assets and ranges.', 15)
    staged, needs_audio = {}, bool(plan['audio'])
    for clip in plan['clips'] + ([plan['audio']] if plan['audio'] else []):
        source, _, _ = media_library.asset_path(root, request['workspace_id'], clip['asset_id'])
        original = next(c for c in approved['clips'] + ([approved['audio']] if approved.get('audio') else []) if c['asset_id'] == clip['asset_id'])
        if source.stat().st_size != original.get('size') or source.stat().st_mtime_ns != original.get('mtime_ns'):
            raise ValueError('An approved media file changed. Select and review the media again.')
        if clip['asset_id'] not in staged:
            if clip['mime'].startswith('video/'):
                needs_audio |= 'audio' in media_library._probe(source, 'video')['streams']
            filename = clip['asset_id'] + source.suffix.lower()
            shutil.copyfile(source, folder / 'assets' / filename)
            if evidence and clip['asset_id'] == evidence['asset_id'] and projects.digest(folder / 'assets' / filename) != evidence['sha256']:
                raise ValueError('The reviewed speech source changed during staging; it was not rendered.')
            staged[clip['asset_id']] = 'assets/' + filename
    vendor = RUNTIME / 'dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js'
    shutil.copyfile(vendor, folder / 'gsap.js')
    from .editor_composition import document as compose
    processed = {}
    cpu_env = {**os.environ, 'DO_NOT_TRACK': '1'}
    for index, clip in enumerate(plan['clips']):
        if clip['effect']['preset'] != 'none' or clip['speed'] != {'start': 1, 'end': 1}:
            progress('effects', f'Preparing filter / speed for clip {index+1}.', 25)
            processed[index] = f'assets/effect-{index}.mp4'
            editor_effects.preprocess(folder / staged[clip['asset_id']], folder / processed[index],
                clip, plan, _run, folder, cpu_env, progress)
    if any(c['transition']['kind'] != 'cut' for c in plan['clips']):
        shutil.copyfile(SHADER, folder / 'shaders.js')
    document, duration = compose(plan, staged, processed=processed)
    (folder / 'index.html').write_text(document)
    # Minimal read-only runtime surface; only this render directory is writable.
    args = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/home', '--dir', '/etc']
    for path in ('/usr', '/lib', '/lib64', '/etc/fonts', '/etc/ld.so.cache', '/etc/alternatives'):
        if Path(path).exists():
            args += ['--ro-bind', path, path]
    args += ['--ro-bind', str(NODE), '/editor-node', '--ro-bind', str(RUNTIME.parent), '/node_modules',
             '--ro-bind', str(BROWSER.parent), '/browser', '--bind', str(folder.resolve()), '/work', '--chdir', '/work',
             '/editor-node', '/node_modules/hyperframes/bin/hyperframes.mjs', 'render', '--output', 'final.mp4',
             '--fps', str(plan['fps']), '--quality', 'high', '--workers', '1', '--no-browser-gpu']
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'TMPDIR': '/tmp',
           'HYPERFRAMES_BROWSER_PATH': '/browser/headless_shell', 'HYPERFRAMES_NO_TELEMETRY': '1',
           'DO_NOT_TRACK': '1', 'CI': '1'}
    _run(args, folder, env, progress)
    final = folder / 'final.mp4'
    probe = media_library._probe(final, 'video')
    if needs_audio and 'audio' not in probe['streams']:
        raise ValueError('The render lost the approved audio stream; it was not published.')
    if abs(probe['duration_seconds'] - duration) > max(.25, 2 / plan['fps']) or (probe['width'], probe['height']) != (plan['width'], plan['height']):
        raise ValueError('The render does not match the approved duration/dimensions; it was not published.')
    while True:
        with state(root) as data:
            p = project(data, request['project_id'])
            paused = p.get('pause_requested', False)
        if not paused:
            break
        progress('paused', 'Render completed. Waiting for Resume before publishing.', 95)
        time.sleep(2)
    progress('publish', 'Final video validated. Registering it in the shared library.', 97)
    with state(root) as data:
        p = project(data, request['project_id'])
        current = video_repertoire.read_job('vibe-editor', job_id)
        if p['revision'] != request['revision'] or current['status'] in {'cancel_requested', 'cancelled'}:
            raise ValueError('Stopped or changed revision; the final video was not published.')
        relative = f'vibe_editor/{request["project_id"]}/{job_id}.mp4'
        destination = generated_root(root, request['workspace_id']) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(final, destination)
        asset = media_library.register_generated_video(root, request['workspace_id'], relative,
            {'editor_project_id': request['project_id'], 'editor_revision': request['revision'], 'editor_job_id': job_id})
        result = {'asset': asset, 'composition_path': str(folder / 'index.html'), 'duration_seconds': duration}
        p['output'] = result
        return result
