"""Pinned CPU Remotion adapter for trusted, reviewed Editor compositions."""
import json
import shutil
from pathlib import Path
from . import vibe_editor_render as renderer

VERSION = '4.0.541'
RUNTIME = renderer.APP / 'local_data/runtimes/remotion'


def capability():
    try:
        pinned = json.loads((RUNTIME / 'vibe-runtime.json').read_text())['version'] == VERSION
        packages = all(json.loads((RUNTIME / 'node_modules' / name / 'package.json').read_text())['version'] == VERSION
                       for name in ('remotion', '@remotion/bundler', '@remotion/renderer'))
    except (OSError, KeyError, ValueError):
        pinned = packages = False
    checks = {'pinned_packages': pinned and packages, 'browser': renderer.BROWSER.is_file(),
              'node': renderer.NODE.is_file(), 'sandbox': bool(shutil.which('bwrap'))}
    return {'ready': all(checks.values()), 'checks': checks, 'version': VERSION,
            'message': 'Pinned Remotion CPU renderer. Install with conda run -n react python scripts/setup_remotion.py if unavailable.'}


def render(folder, plan, staged, processed, progress):
    if not capability()['ready']:
        raise ValueError(capability()['message'])
    # Remotion staticFile serves this one render's assets, never arbitrary filesystem URLs.
    strip = lambda value: value.removeprefix('assets/')
    (folder / 'composition.json').write_text(json.dumps({'plan': plan,
        'sources': {k: strip(v) for k, v in staged.items()}, 'processed': {k: strip(v) for k, v in processed.items()}}))
    shutil.copyfile(Path(__file__).with_suffix('.jsx'), folder / 'entry.jsx')
    shutil.copyfile(Path(__file__).with_suffix('.mjs'), folder / 'render.mjs')
    args = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session', '--proc', '/proc', '--dev', '/dev',
            '--tmpfs', '/tmp', '--dir', '/home', '--dir', '/etc']
    for path in ('/usr', '/lib', '/lib64', '/etc/fonts', '/etc/ld.so.cache', '/etc/alternatives'):
        if Path(path).exists():
            args += ['--ro-bind', path, path]
    args += ['--ro-bind', str(renderer.NODE), '/editor-node', '--ro-bind', str(RUNTIME), '/runtime',
             '--ro-bind', str(renderer.BROWSER.parent), '/browser', '--bind', str(folder.resolve()), '/work',
             '--chdir', '/work', '/editor-node', '/work/render.mjs', '/runtime', '/work', '/browser/headless_shell']
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'TMPDIR': '/tmp', 'DO_NOT_TRACK': '1', 'CI': '1'}
    renderer._run(args, folder, env, progress)
