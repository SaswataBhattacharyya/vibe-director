"""Typed compositing layers shared by preview, Studio and approved CPU rendering."""
import html
import json
import math
import re


def number(value, low, high, label):
    if type(value) not in (float, int) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be a finite number between {low} and {high}.')
    return value


def media_ranges(plan):
    return plan['clips'] + ([plan['audio']] if plan.get('audio') else []) + [layer for layer in plan.get('layers', []) if 'asset_id' in layer]


def validate(root, owner, raw, duration, validate_selection):
    if not isinstance(raw, list) or len(raw) > 100:
        raise ValueError('Use at most 100 composition layers.')
    result, identities = [], set()
    allowed = {'id', 'kind', 'at', 'duration', 'x', 'y', 'width', 'height', 'rotation', 'opacity', 'z',
               'text', 'font_size', 'color', 'shape', 'asset_id', 'start', 'end', 'fit', 'volume', 'motion',
               'filename', 'mime', 'size', 'mtime_ns'}
    for raw_layer in raw:
        if not isinstance(raw_layer, dict) or set(raw_layer) - allowed:
            raise ValueError('Unsupported composition layer fields.')
        identity, kind = raw_layer.get('id'), raw_layer.get('kind')
        if type(identity) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', identity) or identity in identities:
            raise ValueError('Each layer needs a distinct ID using letters, digits, underscores or hyphens.')
        identities.add(identity)
        if kind not in {'text', 'shape', 'image', 'video', 'audio'}:
            raise ValueError('Layer kind must be text, shape, image, video or audio.')
        layer = {'id': identity, 'kind': kind,
                 'at': number(raw_layer.get('at', 0), 0, duration, 'Layer start'),
                 'duration': number(raw_layer.get('duration', duration), .001, duration, 'Layer duration')}
        if layer['at'] + layer['duration'] > duration + .001:
            raise ValueError('A layer must fit within the composition duration.')
        for key, default, low, high in [('x', 0, -7680, 7680), ('y', 0, -7680, 7680),
                ('width', 320, 1, 7680), ('height', 180, 1, 7680), ('rotation', 0, -3600, 3600),
                ('opacity', 1, 0, 1), ('z', 200, 101, 1000), ('volume', 1, 0, 1)]:
            layer[key] = number(raw_layer.get(key, default), low, high, 'Layer ' + key)
        if layer['z'] != int(layer['z']):
            raise ValueError('Layer z must be an integer.')
        layer['fit'] = raw_layer.get('fit', 'contain')
        if layer['fit'] not in {'contain', 'cover'}:
            raise ValueError('Layer framing must be contain or cover.')
        if kind in {'image', 'video', 'audio'}:
            media, = validate_selection(root, owner, [raw_layer])
            if not media['mime'].startswith(kind + '/'):
                raise ValueError('Layer source must match its media kind.')
            if kind != 'image' and layer['duration'] > media['end'] - media['start'] + .001:
                raise ValueError('Layer duration exceeds its selected source range.')
            layer.update(media)
        elif 'asset_id' in raw_layer:
            raise ValueError('Text and shape layers cannot reference media.')
        layer['text'] = raw_layer.get('text', '')
        if type(layer['text']) is not str or len(layer['text']) > 4000:
            raise ValueError('Layer text must be at most 4000 characters.')
        layer['color'] = raw_layer.get('color', '#ffffff')
        if type(layer['color']) is not str or not re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?', layer['color']):
            raise ValueError('Use a hexadecimal layer color.')
        layer['shape'] = raw_layer.get('shape', 'rectangle')
        if layer['shape'] not in {'rectangle', 'ellipse'}:
            raise ValueError('Choose rectangle or ellipse.')
        layer['font_size'] = number(raw_layer.get('font_size', 48), 8, 512, 'Font size')
        motion = raw_layer.get('motion', [])
        if not isinstance(motion, list) or len(motion) > 100 or kind == 'audio' and motion:
            raise ValueError('Use at most 100 visual animation keyframes; audio supports static volume.')
        layer['motion'], previous = [], -1
        for frame in motion:
            if not isinstance(frame, dict) or not frame or set(frame) - {'time', 'x', 'y', 'scale', 'rotation', 'opacity'}:
                raise ValueError('Animation supports time, x, y, scale, rotation and opacity only.')
            time = number(frame.get('time'), 0, layer['duration'], 'Keyframe time')
            if time <= previous:
                raise ValueError('Animation keyframe times must increase strictly.')
            previous = time
            normalized = {'time': time}
            for key, low, high in [('x', -7680, 7680), ('y', -7680, 7680), ('scale', .01, 20), ('rotation', -3600, 3600), ('opacity', 0, 1)]:
                if key in frame:
                    normalized[key] = number(frame[key], low, high, 'Keyframe ' + key)
            layer['motion'].append(normalized)
        result.append(layer)
    return result


def document(layers, sources):
    elements, animations = [], []
    for layer in layers:
        identity = 'layer-' + layer['id']
        tag = {'text': 'div', 'shape': 'div', 'image': 'img', 'video': 'video', 'audio': 'audio'}[layer['kind']]
        attrs = {'id': identity, 'class': 'clip vibe-layer', 'data-start': layer['at'],
                 'data-duration': layer['duration'], 'data-track-index': layer['z']}
        style = f"position:absolute;left:{layer['x']}px;top:{layer['y']}px;width:{layer['width']}px;height:{layer['height']}px;opacity:{layer['opacity']};transform:rotate({layer['rotation']}deg);z-index:{int(layer['z'])};object-fit:{layer['fit']}"
        if layer['kind'] == 'text':
            style += f";font:{layer['font_size']}px sans-serif;color:{layer['color']};white-space:pre-wrap;overflow:hidden"
        if layer['kind'] == 'shape':
            style += f";background:{layer['color']};border-radius:{'50%' if layer['shape']=='ellipse' else '0'}"
        if 'asset_id' in layer:
            attrs.update(src=sources[layer['asset_id']], **{'data-media-start': layer['start'], 'data-volume': layer['volume']})
        attrs['style'] = style
        attr_text = ' '.join(f'{key}="{html.escape(str(value), quote=True)}"' for key, value in attrs.items())
        content = html.escape(layer['text']) if layer['kind'] == 'text' else ''
        elements.append(f'<{tag} {attr_text}>' + (f'{content}</{tag}>' if tag != 'img' else ''))
        previous = 0
        for frame in layer['motion']:
            properties = {k: v for k, v in frame.items() if k != 'time'}
            properties.update(ease='none', duration=frame['time'] - previous)
            animations.append(f'tl.to("#{identity}",{json.dumps(properties)},{layer["at"] + previous});')
            previous = frame['time']
    return ''.join(elements), ''.join(animations)
