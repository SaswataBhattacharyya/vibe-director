"""Versioned Film production approaches, independent of visual treatment."""
import copy

_APPROACHES = {
    'cinematic': ('Cinematic', 'Develop dramatic beats, motivated shots and continuity; review performances, coverage and the assembled film.'),
    'documentary_montage': ('Documentary Montage', 'Prefer verified source footage and evidence-led narration. Keep source URLs, rights and attribution with each asset; never present generated imagery as documentary evidence.'),
    'animated_explainer': ('Animated Explainer', 'Organize the explanation into clear visual beats, concise narration and readable diagrams or animation. Verify claims and synchronize visual reveals with the narration.'),
}


def catalogue():
    return [{'id': key, 'display_name': label, 'guidance': guidance, 'version': 1}
            for key, (label, guidance) in _APPROACHES.items()]


def approach(value, production_type):
    if value is None:
        return None  # Existing selections retain their original guidance and hashes.
    if production_type != 'story_film' or type(value) is not str or value not in _APPROACHES:
        raise ValueError('Choose a Film production style: cinematic, documentary_montage or animated_explainer.')
    return copy.deepcopy(next(item for item in catalogue() if item['id'] == value))
