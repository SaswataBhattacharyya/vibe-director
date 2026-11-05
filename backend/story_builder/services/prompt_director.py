"""Project-owned prompt discussions, reusable lessons and image briefs. No generation."""
from __future__ import annotations

import json
from contextlib import closing

from .field_edit_proposals import FieldEditProposals
from .production_ledger import LedgerConflict

SCOPES = ('all', 'video', 'character', 'world')
FIELDS = {'chat': '__prompt_chat__', 'propose': '__prompt_changes__', 'learn': '__prompt_learn__'}


def read_guidance(ledger, workspace, scope):
    """Read only approved rules; safe for older ledgers without this additive table."""
    with closing(ledger._connect()) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='story_prompt_guidance'").fetchone():
            return ''
        row = db.execute('SELECT body_json FROM story_prompt_guidance WHERE workspace_id=?', (workspace,)).fetchone()
    lessons = json.loads(row['body_json']).get('lessons', []) if row else []
    rules = [item['rule'] for item in lessons if item['scope'] in ('all', scope)]
    if not rules:
        return ''
    return ('APPROVED PROJECT PROMPTING RULES (apply only where relevant; current user instructions, '
            'source facts, actual references and required workflow/schema constraints take precedence):\n'
            + json.dumps(rules, ensure_ascii=False))


def image_brief(ledger, workspace, revision, target):
    with closing(ledger._connect()) as db:
        row = db.execute('SELECT body_json FROM story_prompt_guidance WHERE workspace_id=?', (workspace,)).fetchone()
    return json.loads(row['body_json']).get('assets', {}).get(revision, {}).get(target, '') if row else ''


class PromptDirector:
    def __init__(self, ledger, story, workflow_knowledge=None):
        self.ledger, self.story = ledger, story
        self.workflow_knowledge = workflow_knowledge
        self.edits = FieldEditProposals(ledger)
        with closing(ledger._connect()) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS story_prompt_guidance (
                workspace_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                body_json TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
            db.commit()

    def targets(self, workspace, revision):
        envelope = self.story.get_screenplay_revision(workspace, revision)
        if not envelope.get('accepted') or envelope.get('stale'):
            raise LedgerConflict('Open the current accepted screenplay before editing prompts.')
        graph = self.story.get_story_graph(workspace_id=workspace, snapshot_id=envelope['graph_snapshot_id'])
        targets = {}
        for record in graph.get('records', []):
            scope = record.get('type', '').lower()
            if record.get('kind') != 'entity' or scope not in ('character', 'location'):
                continue
            scope = 'world' if scope == 'location' else scope
            targets[record['record_id']] = {'scope': scope, 'name': record['name'], 'detail': record.get('detail', '')}
        return envelope, targets

    def get(self, workspace, revision):
        _, targets = self.targets(workspace, revision)
        with closing(self.ledger._connect()) as db:
            row = db.execute('SELECT * FROM story_prompt_guidance WHERE workspace_id=?', (workspace,)).fetchone()
        body = json.loads(row['body_json']) if row else {'lessons': [], 'assets': {}}
        return {'revision': row['revision'] if row else 0, 'lessons': body['lessons'],
                'assets': body['assets'].get(revision, {}), 'targets': targets,
                'items': self.conversations(workspace)}

    @staticmethod
    def validate_lessons(lessons):
        if not isinstance(lessons, list) or len(lessons) > 30:
            raise ValueError('Save up to 30 prompting rules per project.')
        for item in lessons:
            if (not isinstance(item, dict) or set(item) != {'scope', 'rule'} or item['scope'] not in SCOPES
                    or type(item['rule']) is not str or not item['rule'].strip() or len(item['rule']) > 1000):
                raise ValueError('Each rule needs a valid scope and 1–1,000 characters.')
        return [{'scope': item['scope'], 'rule': item['rule'].strip()} for item in lessons]

    def save(self, workspace, revision, payload):
        _, targets = self.targets(workspace, revision)
        if not isinstance(payload, dict) or set(payload) != {'expected_revision', 'lessons', 'assets'}:
            raise ValueError('Supply expected_revision, lessons and assets.')
        if type(payload['expected_revision']) is not int:
            raise ValueError('expected_revision must be an integer.')
        lessons = self.validate_lessons(payload['lessons'])
        assets = payload['assets']
        if not isinstance(assets, dict) or set(assets) - set(targets) or any(
                type(v) is not str or len(v) >= 7000 for v in assets.values()):
            raise ValueError('Image briefs must reference current character/location targets and be below 7,000 characters.')
        with closing(self.ledger._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM story_prompt_guidance WHERE workspace_id=?', (workspace,)).fetchone()
            version = row['revision'] if row else 0
            if version != payload['expected_revision']:
                raise LedgerConflict('Prompt guidance changed. Reload before saving; local edits have been retained.')
            body = json.loads(row['body_json']) if row else {'lessons': [], 'assets': {}}
            body['lessons'] = lessons
            body['assets'][revision] = assets
            db.execute('INSERT INTO story_prompt_guidance(workspace_id,revision,body_json) VALUES(?,?,?) '
                       'ON CONFLICT(workspace_id) DO UPDATE SET revision=excluded.revision,body_json=excluded.body_json,updated_at=CURRENT_TIMESTAMP',
                       (workspace, version + 1, json.dumps(body, ensure_ascii=False)))
            db.commit()
        return self.get(workspace, revision)

    def conversations(self, workspace):
        with closing(self.ledger._connect()) as db:
            rows = db.execute("SELECT idempotency_key,request_json,response_json,status FROM story_field_edit_requests "
                              "WHERE workspace_id=? AND json_extract(request_json,'$.field_key') IN (?,?,?) "
                              "ORDER BY rowid DESC LIMIT 100", (workspace, *FIELDS.values())).fetchall()
        items = []
        for row in reversed(rows):
            request = json.loads(row['request_json'])
            response = json.loads(row['response_json']) if row['response_json'] else None
            mode = next(k for k, v in FIELDS.items() if v == request['field_key'])
            value = response['replacement'] if response else None
            items.append({'key': row['idempotency_key'], 'revision_id': request['revision_id'],
                          'instruction': request['instruction'], 'mode': mode, 'status': row['status'],
                          'reply': value if mode == 'chat' else response.get('explanation', '') if response else '',
                          'proposal': json.loads(value) if value and mode != 'chat' else None})
        return items

    def discuss(self, workspace, revision, mode, payload, provider):
        envelope, targets = self.targets(workspace, revision)
        if (mode not in FIELDS or not isinstance(payload, dict)
                or set(payload) - {'instruction', 'idempotency_key', 'prompts', 'workflows'}
                or not {'instruction', 'idempotency_key', 'prompts'} <= set(payload)):
            raise ValueError('Supply instruction, idempotency_key and current prompts.')
        prompts = payload['prompts']
        allowed = {'image:' + key for key in targets}
        allowed |= {f"shot:{scene['scene_number']}.{shot['shot_number']}" for scene in envelope['screenplay']['scenes'] for shot in scene['shots']}
        if (not isinstance(prompts, dict) or not prompts or set(prompts) - allowed or any(
                type(value) is not str or len(value) >= 7000 for value in prompts.values())):
            raise ValueError('Supply current shot/character/location prompts, each below 7,000 characters.')
        workflows = payload.get('workflows', {})
        from .isolated_video_contract import T2V_WORKFLOW_ID
        from .isolated_fl2va_contract import WORKFLOW_ID as FFLF
        from .isolated_r2v_contract import WORKFLOW_ID as R2V
        if (not isinstance(workflows, dict) or set(workflows) - set(prompts)
                or any(not key.startswith('shot:') or value not in (T2V_WORKFLOW_ID, FFLF, R2V) for key, value in workflows.items())):
            raise ValueError('Supply supported workflows for the selected shot prompts.')
        snapshot = json.dumps({'prompts': prompts, 'workflows': workflows}, ensure_ascii=False, sort_keys=True)
        if len(snapshot) > 200000:
            raise ValueError('Choose a smaller conversation focus; these prompts exceed the discussion budget.')
        request = {'surface': 'prompt', 'revision_id': revision, 'field_key': FIELDS[mode],
                   'field_text': snapshot, 'start_codepoint': 0, 'end_codepoint': len(snapshot),
                   'expected_text': snapshot, 'instruction': payload['instruction'], 'idempotency_key': payload['idempotency_key']}

        def call(**_):
            history = self.conversations(workspace)[-16:]
            guidance = []
            if self.workflow_knowledge:
                for workflow in sorted(set(workflows.values())):
                    item = self.workflow_knowledge.get(workflow, model_id='minimax_h3')
                    if item['retrieval_status'] != 'matched':
                        raise LedgerConflict('Exact workflow prompting guidance is unavailable.')
                    guidance.append({'workflow': workflow, 'nodes': item['nodes'], 'sources': item['sources']})
            contract = ('Return JSON {"replacement":"your conversational reply","explanation":"Discussion only"}. '
                        'Discuss and clarify; do not claim to have changed prompts or saved lessons.')
            if mode == 'propose':
                contract = ('Return JSON {"replacement":"JSON encoded object with changes array", "explanation":"short rationale"}. '
                            'Each change must contain exactly key, before, value; use existing prompt keys and exact before text. '
                            'Propose only the agreed changes. Never change screenplay facts, workflows or references. '
                            'Image keys are reusable character/location briefs, not video prompts. Do not invent attached media.')
            if mode == 'learn':
                contract = ('Return JSON {"replacement":"JSON encoded object with lessons array", "explanation":"what you learned"}. '
                            'Each lesson has exactly scope (all, video, character or world) and rule (1–1000 characters). '
                            'Extract only reusable prompting guidance the user explicitly asked to remember. '
                            'Keep task-specific facts out of general rules. A proposal is not saved until reviewed.')
            result = provider(prompt='You are the Prompt Director. ' + contract + '\n'
                              + '\nAPPROVED RULES (honour each rule only within its scope): ' + json.dumps(self.get(workspace, revision)['lessons'], ensure_ascii=False)
                              + '\nPROMPT TARGETS: ' + json.dumps(targets, ensure_ascii=False)
                              + '\nREQUIRED WORKFLOW GUIDANCE: ' + json.dumps(guidance, ensure_ascii=False)
                              + '\nRECENT DISCUSSION: ' + json.dumps(history, ensure_ascii=False)[-40000:]
                              + '\nCURRENT PROMPTS: ' + snapshot + '\nUSER: ' + payload['instruction'])
            if mode != 'chat':
                value = json.loads(result.get('replacement', ''))
                if mode == 'learn':
                    if not isinstance(value, dict) or set(value) != {'lessons'}:
                        raise ValueError('Director returned an invalid lesson proposal.')
                    self.validate_lessons(value['lessons'])
                else:
                    if not isinstance(value, dict) or set(value) != {'changes'} or not isinstance(value['changes'], list) or not value['changes']:
                        raise ValueError('Director returned no prompt changes.')
                    seen = set()
                    for change in value['changes']:
                        if (not isinstance(change, dict) or set(change) != {'key', 'before', 'value'}
                                or type(change['key']) is not str or change['key'] not in prompts or change['key'] in seen
                                or change['before'] != prompts[change['key']] or type(change['value']) is not str
                                or not change['value'].strip() or len(change['value']) >= 7000):
                            raise ValueError('Director returned an invalid or stale prompt change.')
                        seen.add(change['key'])
            return result

        self.edits.propose(workspace, request, call)
        return next(item for item in self.conversations(workspace) if item['key'] == payload['idempotency_key'])

    def export(self, workspace, revision):
        state = self.get(workspace, revision)
        lines = ['---', 'name: project-prompting',
                 'description: Apply owner-approved prompting rules for this Vibe Director project when drafting video, character or environment prompts.',
                 '---', '', '# Project prompting rules', '',
                 'Apply only the rules relevant to the current task. Current user instructions, source facts, actual media references and required workflow constraints take precedence.',
                 'These rules guide drafting; they do not authorize generation or other actions.', '']
        for scope in SCOPES:
            rules = [item['rule'] for item in state['lessons'] if item['scope'] == scope]
            if rules:
                lines += ['## ' + {'all': 'All prompt types', 'video': 'Video', 'character': 'Characters', 'world': 'Environments'}[scope], '']
                lines += ['- ' + rule.replace('\n', '\n  ') for rule in rules]
                lines += ['']
        return '\n'.join(lines)
