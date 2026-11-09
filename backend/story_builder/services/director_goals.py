"""Project-owned H2 objectives and receipts, in the existing task ledger.

No tool execution or approval authority lives here. A started step without a
task receipt is uncertain: recovery must stop rather than repeat the operation.
"""
import json

from . import agent_graph, projects
from .production_ledger import LedgerConflict, LedgerNotFound, _now, stable_hash


class Goals:
    def __init__(self, tasks):
        self.tasks, self.root, self.ledger = tasks, tasks.root, tasks.ledger

    def get(self, owner, request):
        agent_graph.resolve_workspace(self.root, owner)
        with self.ledger._connect() as db:
            row = db.execute('SELECT * FROM director_goals WHERE project_id=? AND request_id=?',
                             (owner, request)).fetchone()
            if row is None:
                raise LedgerNotFound('Director goal not found in this project.')
            goal = dict(row)
            goal['state'] = json.loads(goal.pop('state_json'))
            goal['steps'] = [dict(s) for s in db.execute(
                'SELECT * FROM director_goal_steps WHERE project_id=? AND request_id=? ORDER BY rowid', (owner, request))]
        for step in goal['steps']:
            step['arguments'] = json.loads(step.pop('arguments_json'))
            step['result'] = json.loads(step.pop('result_json') or 'null')
        return goal

    def create(self, owner, request, objective):
        with projects.locked(self.root), self.ledger._connect() as db:
            agent_graph.resolve_workspace(self.root, owner)
            # Serialize active goals per project, including across backend workers.
            if db.execute("SELECT 1 FROM director_goals WHERE project_id=? AND status='running'", (owner,)).fetchone():
                raise LedgerConflict('A Director goal is already running in this project.')
            state = {'engine': 'codex-app-server', 'phase': 'starting', 'progress': '',
                     'dependencies': [], 'authorization': 'read-only-and-draft',
                     'completion_criteria': 'Verified objective output; individual tool completion is insufficient.',
                     'recovery': None, 'stop_reason': None}
            db.execute('INSERT INTO director_goals VALUES (?,?,?,?,?,?,?)',
                       (owner, request, objective, 'running', None, json.dumps(state), _now()))
        return self.get(owner, request)

    def update(self, owner, request, *, status=None, thread_id=None, reply=None, message_status='answered', **changes):
        with projects.locked(self.root), self.ledger._connect() as db:
            goal = self.get(owner, request)
            # Cancellation is terminal, even when an old worker finishes later.
            if goal['status'] == 'cancelled':
                return goal
            goal['state'].update(changes)
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE director_goals SET status=?,thread_id=?,state_json=?,updated_at=? '
                       'WHERE project_id=? AND request_id=?',
                       (status or goal['status'], thread_id or goal['thread_id'], json.dumps(goal['state']),
                        _now(), owner, request))
            if reply is not None:
                db.execute('UPDATE agent_messages SET reply=?,status=? WHERE project_id=? AND request_id=?',
                           (reply[:16000], message_status, owner, request))
            db.commit()
        return self.get(owner, request)

    def step(self, owner, request, tool, arguments):
        key = stable_hash({'tool': tool, 'arguments': arguments})
        with projects.locked(self.root), self.ledger._connect() as db:
            goal = self.get(owner, request)
            if goal['status'] != 'running':
                raise LedgerConflict('Director goal is not authorized to continue.')
            existing = next((s for s in goal['steps'] if s['step_key'] == key), None)
            if existing:
                return existing, False
            if len(goal['steps']) >= 12:
                raise LedgerConflict('Director step budget exhausted; review before continuing.')
            db.execute('INSERT INTO director_goal_steps VALUES (?,?,?,?,?,?,?,?)',
                       (owner, request, key, tool, json.dumps(arguments), None, 'started', None))
        return next(s for s in self.get(owner, request)['steps'] if s['step_key'] == key), True

    def activate(self, owner, request):
        with projects.locked(self.root), self.ledger._connect() as db:
            goal = self.get(owner, request)
            if goal['status'] not in {'running', 'interrupted', 'blocked'}:
                raise LedgerConflict('This goal cannot be resumed.')
            if db.execute("SELECT 1 FROM director_goals WHERE project_id=? AND request_id!=? AND status='running'",
                          (owner, request)).fetchone():
                raise LedgerConflict('Another Director goal is active in this project.')
            db.execute("UPDATE director_goals SET status='running',updated_at=? WHERE project_id=? AND request_id=?",
                       (_now(), owner, request))

    def receipt(self, owner, request, key, *, task_id=None, result=None):
        with projects.locked(self.root), self.ledger._connect() as db:
            # Keep late receipts after cancellation: they are evidence, not permission.
            self.get(owner, request)
            db.execute('UPDATE director_goal_steps SET task_id=COALESCE(?,task_id), '
                       'status=?,result_json=? WHERE project_id=? AND request_id=? AND step_key=?',
                       (task_id, 'completed' if result is not None else 'started',
                        json.dumps(result) if result is not None else None, owner, request, key))

    def message(self, owner, request, reply, status='answered'):
        with projects.locked(self.root), self.ledger._connect() as db:
            db.execute('UPDATE agent_messages SET reply=?,status=? WHERE project_id=? AND request_id=?',
                       (reply[:16000], status, owner, request))

    def public(self, owner, request):
        goal = self.get(owner, request)
        goal['state'].pop('token', None)
        return {key: goal[key] for key in ('request_id', 'objective', 'status', 'thread_id', 'state', 'updated_at')} | {
            'steps': [{key: step[key] for key in ('tool', 'task_id', 'status')} for step in goal['steps']]}
