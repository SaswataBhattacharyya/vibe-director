"""Shared Director adapter for existing prompt discussions and reviewed rules."""


class PromptDirectorAdapter:
    """Delegate shared chat to the existing prompt review and guidance service."""
    def __init__(self, service, provider):
        self.service, self.provider = service, provider

    def context(self, owner, target):
        if (not isinstance(target, dict)
                or set(target) != {'version', 'workspace_id', 'screenplay_revision_id', 'prompts', 'workflows'}
                or type(target['version']) is not int or target['version'] != 1
                or target['workspace_id'] != owner
                or not isinstance(target['screenplay_revision_id'], str)
                or not 1 <= len(target['screenplay_revision_id']) <= 200):
            raise ValueError('Supply versioned prompt context owned by the open project.')
        self.service.context(owner, target['screenplay_revision_id'], target['prompts'], target['workflows'])
        return target

    def respond(self, owner, target, text, request_id, *, mode):
        self.context(owner, target)
        result = self.service.discuss(owner, target['screenplay_revision_id'], mode,
            {'instruction': text, 'idempotency_key': request_id,
             'prompts': target['prompts'], 'workflows': target['workflows']}, self.provider)
        return result['reply']
