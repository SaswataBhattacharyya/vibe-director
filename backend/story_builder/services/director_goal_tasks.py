"""Observe goal-linked protected tasks. Authority stays in AgentTasks approvals.

This module never approves or dispatches. It reconciles durable invocation IDs
and returns bounded, verified evidence for the original Codex objective.
"""
import json

from .production_ledger import LedgerConflict, stable_hash


PROPOSALS = {'editor_propose_session', 'editor_propose_selection'}
WAITING = {'waiting_for_approval', 'waiting_for_execution', 'waiting_for_job'}


def linked(goals, owner, task_id):
    with goals.ledger._connect() as db:
        row = db.execute('SELECT request_id FROM director_goal_steps WHERE project_id=? AND task_id=?',
                         (owner, task_id)).fetchone()
    return goals.get(owner, row[0]) if row else None


def reviewed_step(goal, task):
    step = next(s for s in goal['steps'] if s['task_id'] == task['task_id'])
    saved = step['result'] or {}
    if (saved.get('revision'), saved.get('plan_hash')) != (task['current_revision'], task['plan_hash']):
        raise LedgerConflict('Goal proposal changed since review. Reject it and prepare a new proposal.')
    return step


def validate_action(tasks, owner, task):
    from .director_goals import Goals
    goal = linked(Goals(tasks), owner, task['task_id'])
    if not goal:
        return False
    step = next(s for s in goal['steps'] if s['task_id'] == task['task_id'])
    if step['tool'] not in PROPOSALS:
        return False  # Existing explicit host read policy is unchanged.
    if goal['status'] == 'cancelled' or task['status'] in {'cancelled', 'failed'}:
        raise LedgerConflict('The original goal or protected task is cancelled or failed.')
    reviewed_step(goal, task)
    return True


def snapshot(tasks, goal):
    """Polling may reconcile an existing job, but cannot start/repeat an operation."""
    receipts, pending, states = [], [], []
    for step in goal['steps']:
        if step['tool'] not in PROPOSALS or not step['task_id']:
            continue
        task = tasks.poll(goal['project_id'], step['task_id'])
        reviewed_step(goal, task)
        state = task['status']
        if state in {'cancelled', 'failed', 'recovery_required'}:
            raise LedgerConflict('Protected task is ' + state + '; no automatic execution or retry.')
        if state == 'draft':
            pending.append(task['task_id'])
            states.append('waiting_for_approval')
            continue
        with tasks.ledger._connect() as db:
            approval = db.execute('SELECT approved_at FROM agent_task_approvals WHERE project_id=? '
                'AND task_id=? AND revision=? AND plan_hash=?',
                (goal['project_id'], task['task_id'], task['current_revision'], task['plan_hash'])).fetchone()
        if not approval:
            raise LedgerConflict('Exact protected plan has no saved human approval.')
        receipt = {'task_id': task['task_id'], 'revision': task['current_revision'],
                   'plan_hash': task['plan_hash'], 'approved_at': approval[0], 'status': state,
                   'invocation': task['invocation']}
        if state != 'completed':
            pending.append(task['task_id'])
            states.append('waiting_for_job' if task['invocation'] else 'waiting_for_execution')
        else:
            if not task['invocation'] or not task['invocation'].get('job_id'):
                raise LedgerConflict('Completed protected task has no verified job.')
            # AgentTasks.poll validates the frozen job and its outputs first.
            report = json.loads(task.get('report') or '{}')
            value = report.get('result', {}).get('result', {})
            receipt['result'] = value
            receipt['outputs'] = task['outputs']
            receipt['receipt_sha256'] = stable_hash(receipt)
        receipts.append(receipt)
    if len(json.dumps(receipts).encode()) > 24000:
        raise LedgerConflict('Protected result exceeds continuation context budget.')
    waiting = next((s for s in ('waiting_for_approval', 'waiting_for_execution', 'waiting_for_job') if s in states), None)
    return {'waiting': waiting, 'dependencies': pending, 'protected_tasks': receipts}


def unconsumed(goal, evidence):
    consumed = goal['state'].get('consumed_tasks', {})
    return any(r.get('receipt_sha256') and consumed.get(r['task_id']) != r['receipt_sha256']
               for r in evidence['protected_tasks'])
