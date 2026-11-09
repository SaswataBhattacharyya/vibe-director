"""Install only the pinned, licensed Backlot runtime; no models or provider calls."""
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen

REVISION = 'd21f5d4eaa08422b09c7091757a05affcbabb35b'
DESTINATION = Path(__file__).resolve().parents[1] / 'local_data/runtimes/openmontage'
FILES = ['LICENSE', 'backlot/__init__.py', 'backlot/server.py', 'backlot/state.py',
         'backlot/ui/board.css', 'backlot/ui/board.html', 'backlot/ui/board.js',
         'backlot/ui/index.html', 'backlot/ui/lib.js', 'backlot/ui/library.js',
         'lib/__init__.py', 'lib/paths.py', 'lib/events.py']


def install():
    if DESTINATION.exists():
        raise SystemExit('Runtime already exists; inspect it rather than overwriting it.')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vibe-backlot-install-', dir=DESTINATION.parent) as scratch:
        stage = Path(scratch) / 'source'
        hashes = {}
        for name in FILES:
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with urlopen(f'https://raw.githubusercontent.com/calesthio/OpenMontage/{REVISION}/{name}', timeout=30) as response:
                content = response.read(4 * 1024 * 1024)
            target.write_bytes(content)
            hashes[name] = hashlib.sha256(content).hexdigest()
        (stage / 'vibe-runtime.json').write_text(json.dumps({'revision': REVISION, 'sha256': hashes}, indent=2))
        shutil.move(stage, DESTINATION)
    print(f'Installed pinned read-only Backlot: {DESTINATION}')


if __name__ == '__main__':
    install()
