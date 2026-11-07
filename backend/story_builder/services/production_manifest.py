"""Metadata-only storyboard interchange; Vibe retains media and execution authority."""
from . import media_library, projects
from .production_ledger import LedgerConflict


UPSTREAM_REVISION = 'd21f5d4eaa08422b09c7091757a05affcbabb35b'


def export(board, owner, screenplay_revision, expected_revision):
    saved = board.get(owner, screenplay_revision)
    if type(expected_revision) is not int or expected_revision != saved['revision']:
        raise LedgerConflict('Storyboard changed. Reload and export the saved revision again.')
    body = board.validate(owner, screenplay_revision, saved['body'])
    # Validation returns a copied body; media remain owned catalog occurrences.
    screenplay = board.screenplay(owner, screenplay_revision)['screenplay']
    assets = board.assets(owner)
    sections, scenes, manifest, mapping = [], [], [], []
    verified, position = {}, 0.0
    for scene in screenplay['scenes']:
        number = scene['scene_number']
        for shot in scene['shots']:
            key = f"{number}.{shot['shot_number']}"
            prepared = body['shots'][key]
            identity = f'{owner}:{screenplay_revision}:{key}'
            end = position + prepared['duration']
            sections.append({'id': identity, 'label': f'Scene {number} · Shot {shot["shot_number"]}',
                             'text': shot.get('dialogue', ''), 'start_seconds': position, 'end_seconds': end})
            required = list(dict.fromkeys(filter(None, [prepared['background_asset_id'],
                *prepared['reference_ids'], prepared['first_frame_id'], prepared['last_frame_id'],
                prepared['image_asset_id'], prepared['media_asset_id']])))
            scenes.append({'id': identity, 'script_section_id': identity, 'type': prepared['presentation'],
                'description': prepared['prompt'], 'start_seconds': position, 'end_seconds': end,
                'required_assets': required, 'shot_intent': shot.get('action', '')})
            mapping.append({'scene_id': identity, 'scene_number': number, 'shot_number': shot['shot_number'],
                            'shot_key': key, 'notes': prepared['notes'], 'route': prepared['route'],
                            'scene_description': body['scenes'][str(number)]['description']})
            for aid in required:
                asset = assets[aid]
                if aid not in verified:
                    path, _, _ = media_library.asset_path(board.root, owner, aid)
                    if projects.digest(path) != asset['sha256']:
                        raise LedgerConflict('A storyboard source changed. Re-register and review its current bytes.')
                    verified[aid] = asset
                # Backlot resolves only local project paths. An API URL is not one.
                manifest.append({'id': f'{identity}:{aid}', 'scene_id': identity, 'type': asset['kind'],
                    'path': '', 'vibe_asset_id': aid, 'sha256': asset['sha256'],
                    'filename': asset['filename'], 'content_url': asset['content_url'],
                    'roles': asset['roles'], 'source_tool': 'vibe-director'})
            position = end
    # Reject a concurrent save rather than labeling a stale export current.
    if board.get(owner, screenplay_revision)['revision'] != expected_revision:
        raise LedgerConflict('Storyboard changed during export. Export the current revision again.')
    return {'schema': 'vibe-director.production-manifest', 'version': 1,
        'upstream': {'repository': 'calesthio/OpenMontage', 'revision': UPSTREAM_REVISION,
                     'license': 'AGPL-3.0', 'interface': 'Backlot read-only artifacts'},
        'project': {'workspace_id': owner, 'screenplay_revision_id': screenplay_revision,
                    'storyboard_revision': expected_revision, 'title': screenplay.get('title', '')},
        'capabilities': {'metadata_only': True, 'media_bundled': False, 'write_back': False,
                         'timing': 'planned storyboard duration; not source in/out ranges'},
        'shot_mapping': mapping, 'artifacts': {'script': {'sections': sections},
            'scene_plan': {'scenes': scenes, 'metadata': {'total_duration_seconds': position}},
            'asset_manifest': {'assets': manifest}}}
