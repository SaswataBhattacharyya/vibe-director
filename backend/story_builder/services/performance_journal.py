"""Opt-in H3 wall-clock measurements. Recording never changes workload admission."""
import json
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from .debug_journal import DebugJournal

LOGGER = logging.getLogger(__name__)


class PerformanceJournal(DebugJournal):
    FIELDS = DebugJournal.FIELDS | {'project_id', 'take_id', 'phase', 'seconds',
        'workflow_id', 'duration_seconds', 'width', 'height', 'recovered', 'pipeline_stage'}

    def __init__(self, root):
        super().__init__(root)
        self.directory = Path(root) / 'reports/performance'
        self.policy_path = self.directory / 'policy.json'

    def summary(self):
        status = self.status()
        # Bounded inherited log limit. No prompts, references or media content.
        rows = []
        for line in self.read_log().splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except (ValueError, UnicodeDecodeError):
                # Another process may still be appending the final record.
                continue
        return {**status, 'recent': [row for row in rows if row.get('kind') == 'timing'][-30:]}

    def measure(self, take, phase, seconds, outcome='completed', recovered=False):
        try:
            request = take.get('input_snapshot') or {}
            self.record([{'kind': 'timing', 'project_id': take.get('project_id', ''),
                'take_id': take.get('take_id', ''), 'phase': phase,
                'seconds': round(max(0, seconds), 3), 'outcome': outcome,
                'workflow_id': request.get('workflow_id', 'minimax_h3_t2v_local_v1'),
                **{key: request[key] for key in ('duration_seconds', 'width', 'height') if key in request},
                'recovered': recovered, 'pipeline_stage': (take.get('pipeline') or {}).get('stage', 'turbo_original' if request.get('workflow_version') == 2 else 'single_stage')}])
        except Exception:
            # A full/unwritable journal must not fail or retry a render.
            LOGGER.warning('Performance recording unavailable', exc_info=True)

    @contextmanager
    def phase(self, take, name):
        started = time.monotonic()
        outcome = 'completed'
        try:
            yield
        except BaseException:
            outcome = 'error'
            raise
        finally:
            self.measure(take, name, time.monotonic() - started, outcome)

    def execution_history(self, take, history):
        """Execution is inclusive (encoders, denoise, VAE, mux), not denoise alone."""
        try:
            stamps = {}
            for item in (history.get('status') or {}).get('messages', []):
                if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], dict):
                    stamp = item[1].get('timestamp')
                    if item[0] in {'execution_start', 'execution_success'} and isinstance(stamp, (int, float)):
                        stamps[item[0]] = stamp
            if len(stamps) == 2 and stamps['execution_success'] >= stamps['execution_start']:
                self.measure(take, 'comfy_execution_inclusive',
                    (stamps['execution_success'] - stamps['execution_start']) / 1000)
        except Exception:
            LOGGER.warning('ComfyUI execution timing unavailable', exc_info=True)
