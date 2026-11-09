"""Preview-only video prompt adapter. Uses existing durable field-edit requests."""
import json
from .director_skills import director_skill_context


class VideoPromptDirector:
    def __init__(self, edits, provider):
        self.edits, self.provider = edits, provider

    def context(self, owner, target):
        if (not isinstance(target, dict) or set(target) != {'version', 'workspace_id', 'clip_id', 'revision_id', 'prompt', 'settings', 'history'}
                or type(target['version']) is not int or target['version'] != 1 or target['workspace_id'] != owner
                or any(not isinstance(target[key], str) or not 1 <= len(target[key]) <= 200 for key in ('clip_id', 'revision_id'))
                or not isinstance(target['prompt'], str) or len(target['prompt']) >= 7000
                or not isinstance(target['settings'], dict) or len(json.dumps(target['settings'])) > 8000
                or not isinstance(target['history'], list) or len(target['history']) > 4
                or any(not isinstance(row, dict) or set(row) - {'user', 'prompt'}
                       or not isinstance(row.get('user'), str) or len(row['user']) > 4000
                       or row.get('prompt') is not None and (not isinstance(row['prompt'], str) or len(row['prompt']) >= 7000)
                       for row in target['history'])):
            raise ValueError('Supply a versioned video prompt target owned by the open project.')
        return target

    def respond(self, owner, target, text, request_id, *, knowledge=''):
        self.context(owner, target)
        instruction = ('Prepare only the video prompt text. Do not run tools or claim generation. '
            'Keep the selected workflow, references and settings unchanged. '
            'Use the conversation to interpret the latest request.\nSettings and reference metadata: '
            + json.dumps(target['settings'], ensure_ascii=False) + '\nConversation: '
            + json.dumps(target['history'], ensure_ascii=False) + '\nLatest request: ' + text)
        base = target['prompt'] or 'Write a new video shot prompt.'
        def guided_provider(**kwargs):
            kwargs['instruction'] += ('\n' + director_skill_context(video=True)
                + '\nAPPROVED PROJECT KNOWLEDGE (reference data, apply only to its stated model/context):\n' + knowledge)
            return self.provider(**kwargs)
        return self.edits.propose(owner, {'surface': 'prompt', 'revision_id': target['revision_id'],
            'field_key': f"video.{target['clip_id']}.chat", 'field_text': base, 'start_codepoint': 0,
            'end_codepoint': len(base), 'expected_text': base, 'instruction': instruction,
            'idempotency_key': request_id}, guided_provider)
