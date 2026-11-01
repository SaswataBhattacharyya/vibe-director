"""Launcher lifecycle with mocked services; never starts an app, provider or GPU job."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest


class AppLauncherTests(unittest.TestCase):
    def test_starts_missing_image_worker_and_stops_only_owned_process(self):
        launcher = Path(__file__).resolve().parents[3] / 'start_vibe_director.sh'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            shutil.copy2(launcher, root / launcher.name)
            (root / 'backend').mkdir()
            vite = root / 'frontend/node_modules/.bin/vite'
            vite.parent.mkdir(parents=True)
            vite.write_text('#!/bin/sh\nexit 99\n')
            vite.chmod(0o700)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            def script(path, body):
                path.write_text('#!/bin/sh\n' + body)
                path.chmod(0o700)
            script(bin_dir / 'conda', 'printf "%s/conda\\n" "$LAUNCH_TEST_ROOT"\n')
            script(bin_dir / 'node', 'exit 0\n')
            script(bin_dir / 'xdg-open', 'exit 0\n')
            script(bin_dir / 'curl', '''
case "$*" in
  *images/worker*) test -f "$LAUNCH_TEST_ROOT/worker-pid" || exit 22
                  printf '{"available":true}' ;;
  *3020*) printf '{"backend":{"connected":true}}' ;;
  *8082*) printf 'Vibe Director' ;;
  *) exit 22 ;;
esac
''')
            worker = root / 'conda/envs/react/bin/python'
            worker.parent.mkdir(parents=True)
            script(worker, '''
test "$*" = '-m story_builder.isolated_image_worker --enable-worker' || exit 98
test "$VIBE_DIRECTOR_DATA_DIR" = "$LAUNCH_TEST_ROOT/local_data" || exit 97
printf '%s' "$$" > "$LAUNCH_TEST_ROOT/worker-pid"
exec sleep 300
''')
            env = {**os.environ, 'PATH': str(bin_dir) + ':' + os.environ['PATH'], 'LAUNCH_TEST_ROOT': str(root)}
            output = root / 'launcher.log'
            with output.open('w') as stream:
                process = subprocess.Popen(['bash', str(root / launcher.name)], env=env,
                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if 'Vibe Director is ready:' in output.read_text():
                        break
                    if process.poll() is not None:
                        self.fail(output.read_text())
                    time.sleep(.05)
                self.assertIn('Vibe Director is ready:', output.read_text())
                self.assertIn('backend is already running; reusing it', output.read_text())
                self.assertIn('frontend is already running; reusing it', output.read_text())
                worker_pid = int((root / 'worker-pid').read_text())
                os.kill(worker_pid, 0)
                process.terminate()
                process.wait(timeout=5)
                with self.assertRaises(ProcessLookupError):
                    os.kill(worker_pid, 0)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


if __name__ == '__main__':
    unittest.main()
