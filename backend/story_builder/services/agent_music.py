"""Route shared Director messages through the existing revision-bound ACE chat job."""
from . import ace_studio


def context(root, owner, target):
    if (not isinstance(target, dict) or set(target) != {'version', 'workspace_id', 'project_id', 'revision'}
            or type(target['version']) is not int or target['version'] != 1
            or target['workspace_id'] != owner or not isinstance(target['project_id'], str)
            or type(target['revision']) is not int or target['revision'] < 0):
        raise ValueError('Supply a versioned music session owned by the current project.')
    with ace_studio.state(root) as data:
        project = ace_studio.project(data, target['project_id'])
        if project['workspace_id'] != owner or project['revision'] != target['revision']:
            raise ValueError('This music session changed. Reload before continuing.')
        ace_studio.unlocked(project)
    return target


def discuss(root, owner, target, text):
    context(root, owner, target)
    ace_studio.command(root, target['project_id'], {'action': 'chat', 'revision': target['revision'], 'text': text})
    return 'Preparing the music brief. Review the session response, settings and questions before confirming generation or training.'
