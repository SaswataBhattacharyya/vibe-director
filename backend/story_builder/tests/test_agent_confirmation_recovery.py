"""Real process death around existing durable protected-task dispatch.

No Codex/native input in this fault test. A trusted-host fixture records approval;
the CPU adapter is real, scheduling/crash location is controlled in a child.
"""
import json
import os
import subprocess
import sys
import uuid

from story_builder.services import vibe_editor, video_repertoire
from story_builder.tests.test_agent_tasks import AgentTaskFixture
from story_builder.services.director_goals import Goals
from story_builder.services.director_mcp import Gateway

CHILD = r'''
import json, os, sys
from pathlib import Path
from story_builder.services import agent_native_tools, agent_workspace_tools, projects, video_repertoire
from story_builder.services.agent_tasks import AgentTasks
from story_builder.services.production_ledger import ProductionLedger
root, owner, ident, boundary = Path(sys.argv[1]), *sys.argv[2:]
video_repertoire.configure_roots(root)
tasks = AgentTasks(root, ProductionLedger(projects.database_path(root, projects.DATABASES[0])))
row = tasks.get(owner, ident)
exact = {'revision': row['current_revision'], 'plan_hash': row['plan_hash']}
if boundary == 'before_approval': os._exit(83)
if row['status'] == 'draft': tasks.approve(owner, ident, exact)
if boundary == 'after_approval': os._exit(83)
if boundary == 'before_dispatch':
    agent_native_tools.submit = lambda *a, **kw: os._exit(83)
elif boundary == 'after_creation':
    tasks._map_job = lambda *a, **kw: os._exit(83)
def dispatch(kind, ident):
    if boundary == 'during_CPU_effect':
        job = video_repertoire.read_job(kind, ident)
        job.update(status='running', pid=os.getpid())
        video_repertoire._atomic_json(video_repertoire.job_path(kind, ident), job)
        agent_workspace_tools.run(root, ident, job['request'])
    os._exit(83)
video_repertoire.start_job = dispatch
tasks.run(owner, ident, exact)
raise AssertionError('Crash boundary not reached')
'''


class ProcessRecoveryTests(AgentTaskFixture):
    def check_boundary(self, boundary):
        self.request = str(uuid.uuid4())
        self.goals = Goals(self.tasks)
        self.goals.create(self.owner, self.request, "Create a disposable edit")
        self.goals.update(self.owner, self.request, token="host-only")
        gateway = Gateway(self.tasks, self.owner, self.request, "host-only")
        draft = gateway.call('editor_propose_session', {'name': 'crash ' + boundary})
        row = self.tasks.get(self.owner, draft['task_id'])
        before = set((self.root / 'services/media/jobs/agent-workspace').glob('*/job.json'))
        child = subprocess.run([sys.executable, '-c', CHILD, str(self.root), self.owner, row['task_id'], boundary],
            env={**os.environ, 'VIBE_DIRECTOR_DATA_DIR': str(self.root)}, capture_output=True, text=True, timeout=20)
        self.assertEqual(child.returncode, 83, child.stderr)
        saved = self.tasks.poll(self.owner, row['task_id'])
        self.assertEqual(self.goals.get(self.owner, self.request)['thread_id'], None)
        if boundary == 'before_approval':
            self.assertEqual(saved['status'], 'draft')
        elif boundary == 'after_approval':
            self.assertEqual(saved['status'], 'approved')
        elif boundary == 'before_dispatch':
            self.assertEqual(saved['status'], 'recovery_required')
            self.assertIsNone(saved['invocation']['job_id'])
        else:
            self.assertIsNotNone(saved['invocation']['job_id'])
            if boundary == 'during_CPU_effect':
                self.assertEqual(saved['status'], 'recovery_required')
                self.assertEqual(video_repertoire.read_job('agent-workspace', saved['invocation']['job_id'])['status'], 'interrupted')
                with vibe_editor.state(self.root, readonly=True) as state:
                    self.assertEqual(len(state['projects']), 1)
            # Existing durable job is reconciled; no worker is dispatched again.
            again = self.tasks.run(self.owner, row['task_id'], self.approval(row))
            self.assertEqual(again['invocation'], saved['invocation'])
        after = set((self.root / 'services/media/jobs/agent-workspace').glob('*/job.json'))
        self.tasks.poll(self.owner, row['task_id'])
        self.assertEqual(set((self.root / 'services/media/jobs/agent-workspace').glob('*/job.json')), after)
        self.assertEqual(len(after - before), int(boundary in {'after_creation', 'after_mapping', 'during_CPU_effect'}))
        self.assertEqual(self.original.read_bytes(), self.before)
        self.dispatch.assert_not_called()

    def test_before_approval(self):
        self.check_boundary("before_approval")

    def test_after_approval(self):
        self.check_boundary("after_approval")

    def test_before_dispatch(self):
        self.check_boundary("before_dispatch")

    def test_after_creation(self):
        self.check_boundary("after_creation")

    def test_after_mapping(self):
        self.check_boundary("after_mapping")

    def test_during_cpu_effect(self):
        self.check_boundary("during_CPU_effect")
