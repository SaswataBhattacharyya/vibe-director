"""Build the pinned MCP runtime privately; never replace system packages or installs."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

REVISION = 'b1ff6d5d0263c9074230b9a5d02a6a5d58d2386e'
DESTINATION = Path(__file__).resolve().parents[1] / 'local_data/runtimes/kdenlive-mcp'


def install():
    if DESTINATION.exists():
        raise SystemExit('Runtime already exists; inspect it rather than overwriting it.')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='kdenlive-install-', dir=DESTINATION.parent) as scratch:
        folder = Path(scratch)
        source, tools = folder / 'source', folder / 'tools'

        def run(*args, cwd=folder):
            subprocess.run(args, cwd=cwd, check=True, timeout=600)

        run('git', 'clone', '--no-checkout', 'https://github.com/AMMIROSOH/Kdenlive-mcp.git', str(source))
        run('git', 'checkout', '--detach', REVISION, cwd=source)
        run('npm', 'install', '--prefix', str(tools), '--cache', str(folder / 'npm-cache'),
            '--ignore-scripts', '--no-audit', '--no-fund', 'pnpm@9.5.0')
        pnpm = str(tools / 'node_modules/.bin/pnpm')
        run(pnpm, 'install', '--frozen-lockfile', '--ignore-scripts', '--store-dir', str(folder / 'pnpm-store'), cwd=source)
        run(pnpm, 'build', cwd=source)
        (source / 'vibe-runtime.json').write_text(json.dumps({'revision': REVISION, 'pnpm': '9.5.0'}))
        shutil.rmtree(source / '.git')
        source.rename(DESTINATION)
    print(f'Installed {REVISION} at {DESTINATION}. Run the CPU acceptance before enabling it.')


if __name__ == '__main__':
    install()
