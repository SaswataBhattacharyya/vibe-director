"""Install pinned Remotion packages privately; no model, browser download or render."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

VERSION = '4.0.541'
DESTINATION = Path(__file__).resolve().parents[1] / 'local_data/runtimes/remotion'


def install():
    if DESTINATION.exists():
        raise SystemExit('Remotion runtime exists; inspect it rather than overwriting it.')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vibe-remotion-install-', dir=DESTINATION.parent) as temporary:
        folder = Path(temporary)
        dependencies = {name: VERSION for name in ('remotion', '@remotion/bundler', '@remotion/renderer')}
        dependencies.update({'react': '19.2.0', 'react-dom': '19.2.0'})
        (folder / 'package.json').write_text(json.dumps({'private': True, 'dependencies': dependencies}))
        subprocess.run(['npm', 'install', '--ignore-scripts', '--no-audit', '--no-fund', '--cache', str(folder / '.cache')],
                       cwd=folder, check=True, timeout=600)
        shutil.rmtree(folder / '.cache')
        (folder / 'vibe-runtime.json').write_text(json.dumps({'version': VERSION, 'dependencies': dependencies}))
        folder.rename(DESTINATION)
    print(f'Installed Remotion {VERSION} in {DESTINATION}; package licenses remain in node_modules.')


if __name__ == '__main__':
    install()
