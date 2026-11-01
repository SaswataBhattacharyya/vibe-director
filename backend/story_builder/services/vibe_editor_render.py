"""Trusted JSON-to-HyperFrames adapter. No provider-authored HTML or shell execution."""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root, checked, project_root
import html
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from . import media_library, video_repertoire, editor_effects

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
    folder = checked(project_root(root, request['workspace_id']), 'editor', 'editor', request['project_id'], 'renders', job_id)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'assets').mkdir()
    write(folder / 'plan.json', {'revision': request['revision'], 'style': request['style_snapshot'], 'plan': plan})
    progress('stage', 'Staging only the approved assets and ranges.', 15)
    staged = {}
    for clip in plan['clips'] + ([plan['audio']] if plan['audio'] else []):
        source, _, _ = media_library.asset_path(root, request['workspace_id'], clip['asset_id'])
        original = next(c for c in approved['clips'] + ([approved['audio']] if approved.get('audio') else []) if c['asset_id'] == clip['asset_id'])
        if source.stat().st_size != original.get('size') or source.stat().st_mtime_ns != original.get('mtime_ns'):
            raise ValueError('An approved media file changed. Select and review the media again.')
        if clip['asset_id'] not in staged:
            filename = clip['asset_id'] + source.suffix.lower()
            shutil.copyfile(source, folder / 'assets' / filename)
            staged[clip['asset_id']] = 'assets/' + filename
    vendor = RUNTIME / 'dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js'
    shutil.copyfile(vendor, folder / 'gsap.js')
    duration, elements, animations, transitions, scenes = 0.0, [], [], [], []
    has_transitions = any(c['transition']['kind'] != 'cut' for c in plan['clips'])
    cpu_env = {**os.environ, 'DO_NOT_TRACK': '1'}
    for index, clip in enumerate(plan['clips']):
        length = clip['render_duration']
        source_start = clip['start']
        media = staged[clip['asset_id']]
        if clip['effect']['preset'] != 'none' or clip['speed'] != {'start': 1, 'end': 1}:
            progress('effects', f'Preparing filter / speed for clip {index+1}.', 25)
            media = f'assets/effect-{index}.mp4'
            editor_effects.preprocess(folder / staged[clip['asset_id']], folder / media,
                clip, plan, _run, folder, cpu_env, progress)
            source_start = 0
        attrs = f'id="clip-{index}" class="clip" data-start="{duration}" data-duration="{length}" data-track-index="{index}"'
        src = html.escape(media, quote=True)
        fit = clip['fit']
        if clip['mime'].startswith('video/') or media.endswith(f'effect-{index}.mp4'):
            sound = 'muted' if plan['audio'] else 'data-has-audio="true"'
            element = f'<video {attrs} data-media-start="{source_start}" {sound} playsinline src="{src}" style="object-fit:{fit}"></video>'
        else:
            element = f'<img {attrs} src="{src}" style="object-fit:{fit}"/>'
        if clip['caption']:
            element += f'<div id="caption-{index}" class="clip caption" data-start="{duration}" data-duration="{length}" data-track-index="{index+50}">{html.escape(clip["caption"])}</div>'
        scenes.append(f'scene-{index}')
        elements.append(f'<div id="scene-{index}" class="scene" style="opacity:{1 if index==0 or not has_transitions else 0}">{element}</div>')
        animations.append(f'tl.to({{}}, {{duration:{length}}}, {duration});')
        duration += length
        if index < len(plan['clips'])-1:
            transition = clip['transition']
            duration -= transition['duration']
            transitions.append({'time': duration, 'duration': transition['duration'],
                                **({'shader': transition['kind']} if transition['kind'] not in {'cut', 'dissolve'} else {})})
    shader_script = ''
    if has_transitions:
        shutil.copyfile(SHADER, folder / 'shaders.js')
        shader_script = '<script src="shaders.js"></script>'
        animations.append('HyperShader.init(' + json.dumps({'scenes': scenes, 'transitions': transitions, 'bgColor': '#000'})[:-1] + ',timeline:tl});')
    if plan['audio']:
        audio = plan['audio']
        elements.append(f'<audio id="soundtrack" class="clip" data-start="0" data-duration="{min(duration, audio["end"]-audio["start"])}" data-track-index="100" data-media-start="{audio["start"]}" data-volume="1" src="{html.escape(staged[audio["asset_id"]], quote=True)}"></audio>')
    document = f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#000;width:100%;height:100%;overflow:hidden}}#main{{position:absolute;inset:0}}.scene{{position:absolute;inset:0}}video,img{{position:absolute;inset:0;width:100%;height:100%}}.caption{{position:absolute;left:10%;right:10%;bottom:10%;z-index:2;color:white;text-shadow:0 2px 4px black;font:48px sans-serif;text-align:center;white-space:pre-wrap}}
</style></head><body><div id="main" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="{plan['width']}" data-height="{plan['height']}">{''.join(elements)}</div><script src="gsap.js"></script>{shader_script}<script>window.__timelines={{}};const tl=gsap.timeline({{paused:true}});{''.join(animations)}window.__timelines.main=tl;</script></body></html>'''
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
