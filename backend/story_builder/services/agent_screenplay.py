"""Shared Director adapter for the existing revisioned screenplay conversation."""


class ScreenplayDirector:
    def __init__(self, board, provider):
        self.board, self.provider = board, provider

    def context(self, owner, target):
        if (not isinstance(target, dict)
                or set(target) != {'version', 'workspace_id', 'screenplay_revision_id'}
                or type(target['version']) is not int or target['version'] != 1
                or target['workspace_id'] != owner
                or not isinstance(target['screenplay_revision_id'], str)
                or not 1 <= len(target['screenplay_revision_id']) <= 200):
            raise ValueError('Supply a versioned screenplay target owned by the open project.')
        self.board.screenplay(owner, target['screenplay_revision_id'])
        return target

    def respond(self, owner, target, text, request_id, *, propose):
        self.context(owner, target)
        operation = self.board.propose if propose else self.board.chat
        result = operation(owner, target['screenplay_revision_id'],
            {'instruction': text, 'idempotency_key': request_id}, self.provider)
        return result['explanation'] if propose else result['reply']

