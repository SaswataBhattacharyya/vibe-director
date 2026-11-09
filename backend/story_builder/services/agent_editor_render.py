"""Exact-task approval can approve only the current, already prepared render plan."""
import copy
from . import editor_layers, vibe_editor


def prepare(root, owner, settings):
    with vibe_editor.state(root, readonly=True) as data:
        p = vibe_editor.project(data, settings['project_id'])
        vibe_editor.busy(p)
        pending = p.get('pending')
        if p['workspace_id'] != owner or settings['revision'] != p['revision']:
            raise ValueError('Editor project ownership or revision changed.')
        if not p.get('brief') or not pending or pending['kind'] != 'plan' or pending['revision'] != p['revision']:
            raise ValueError('Prepare and review the Editor media/tool plan before proposing a render.')
        vibe_editor.selected_plan(root, p, pending['value'])
        return copy.deepcopy(pending)


def ranges(settings):
    plan = settings['snapshot']['value']
    return editor_layers.media_ranges(plan)


def submit(root, settings):
    return vibe_editor.command(root, settings['project_id'], {'action': 'approve', 'revision': settings['revision']})
