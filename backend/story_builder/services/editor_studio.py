"""Native Studio drafts map back to typed, revisioned Vibe proposals only."""
import copy
import html
import json
import math
import shutil
from html.parser import HTMLParser
from pathlib import Path

from . import editor_layers, interface_sessions as sessions, media_library, projects, vibe_editor
from .vibe_editor_render import NODE, RUNTIME


def stage(root, project_id, body):
    if not isinstance(body, dict) or set(body) != {'revision', 'plan'}:
        raise ValueError('Supply exactly revision and plan.')
    if json.loads((RUNTIME / 'package.json').read_text())['version'] != '0.8.199':
        raise ValueError('Native Studio requires the verified HyperFrames 0.8.199 runtime.')
    with vibe_editor.state(root, readonly=True) as data:
        p = vibe_editor.project(data, project_id)
        vibe_editor.busy(p)
        if type(body['revision']) is not int or body['revision'] != p['revision']:
            raise ValueError('Stale revision. Refresh before opening Studio.')
        plan = vibe_editor.selected_plan(root, p, body['plan'])
        if any(c['effect']['preset'] != 'none' or c['speed'] != {'start': 1, 'end': 1}
               or c['transition']['kind'] != 'cut' for c in plan['clips']):
            raise ValueError('Native Studio synchronization currently supports 1× hard cuts. Keep effects/speed/transitions in the Vibe visual editor, or reset them before opening Studio.')
        s = sessions.create(root, 'studio', project_id)
        try:
            s.update(revision=p['revision'], plan=copy.deepcopy(plan), hashes={})
            assets = s['folder'] / 'assets'
            assets.mkdir()
            sources = {}
            _, catalog = media_library._manifest(media_library.media_root(root, p['workspace_id']))
            for clip in editor_layers.media_ranges(plan):
                aid = clip['asset_id']
                if aid in sources:
                    continue
                source, _, _ = media_library.asset_path(root, p['workspace_id'], aid)
                target = assets / f'{aid}{source.suffix}'
                digest = projects.digest(source)
                record = media_library._owned_record(root, p['workspace_id'], catalog, aid)
                if not record or digest != record['sha256']:
                    raise ValueError('Registered source bytes changed. Re-register and review this source.')
                shutil.copyfile(source, target)
                if projects.digest(target) != digest:
                    raise ValueError('Source changed while opening Studio. Reopen it.')
                s['hashes'][aid] = digest
                sources[aid] = f'assets/{target.name}'
            s['sources'] = sources
            (s['folder'] / 'index.html').write_text(document(plan, sources))
            shutil.copyfile(RUNTIME / 'dist/vendor/npm/gsap@3.15.0/dist/gsap.min.js', s['folder'] / 'gsap.js')
            return s
        except BaseException:
            sessions.close(s)
            raise


def open_workspace(root, project_id, body):
    s = stage(root, project_id, body)
    result = sessions.launch(s, [NODE, Path(__file__).with_name('native_studio.mjs'), RUNTIME, s['folder']])
    return {**result, 'revision': s['revision']}


def document(plan, sources):
    elements, position = [], 0.0
    for i, clip in enumerate(plan['clips']):
        tag = 'video' if clip['mime'].startswith('video/') else 'img'
        attrs = f'id="clip-{i}" class="clip" data-start="{position}" data-duration="{clip["render_duration"]}" data-media-start="{clip["start"]}" data-track-index="{i}"'
        source = html.escape(sources[clip['asset_id']], quote=True)
        sound = ' muted' if plan['audio'] else ''
        elements.append(f'<{tag} {attrs} src="{source}" style="object-fit:{clip["fit"]};position:absolute;inset:0;width:100%;height:100%"' + (f' playsinline{sound}></video>' if tag == 'video' else '>'))
        # Always expose a caption layer so empty captions can be edited natively.
        elements.append(f'<div id="caption-{i}" class="clip" data-start="{position}" data-duration="{clip["render_duration"]}" data-track-index="{i+50}" style="position:absolute;bottom:10%;left:10%;right:10%;text-align:center;color:white;font:32px sans-serif">{html.escape(clip["caption"])}</div>')
        position += clip['render_duration']
    if plan['audio']:
        a = plan['audio']
        elements.append(f'<audio id="soundtrack" class="clip" data-start="0" data-duration="{min(position,a["end"]-a["start"])}" data-media-start="{a["start"]}" data-track-index="100" src="{html.escape(sources[a["asset_id"]],quote=True)}"></audio>')
    layer_elements, layer_animations = editor_layers.document(plan.get('layers', []), sources)
    elements.append(layer_elements)
    return f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:black}}#main{{position:absolute;inset:0;overflow:hidden}}</style></head><body><div id="main" data-composition-id="main" data-width="{plan["width"]}" data-height="{plan["height"]}" data-duration="{position}">{"".join(elements)}</div><script src="gsap.js"></script><script>const tl=gsap.timeline({{paused:true}}).to({{}},{{duration:{position}}});{layer_animations}window.__timelines={{main:tl}};</script></body></html>'


class _Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements, self.caption = {}, None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identity = attrs.get('id', '')
        if identity in self.elements:
            raise ValueError('Studio contains duplicate layer identities.')
        if identity:
            self.elements[identity] = {**attrs, 'tag': tag, 'text': ''}
        if identity.startswith(('caption-', 'layer-')) and tag == 'div':
            self.caption = identity

    def handle_endtag(self, tag):
        if tag == 'div':
            self.caption = None

    def handle_data(self, text):
        if self.caption:
            self.elements[self.caption]['text'] += text


def mapped_plan(s):
    text = (s['folder'] / 'index.html').read_text()
    if len(text) > 1024 * 1024:
        raise ValueError('Studio composition is too large.')
    elements = _Elements(text).elements
    plan, timed = copy.deepcopy(s['plan']), []
    expected = {'main', *[f'clip-{i}' for i in range(len(plan['clips']))],
                *[f'caption-{i}' for i in range(len(plan['clips']))]}
    expected.update('layer-' + layer['id'] for layer in plan.get('layers', []))
    if plan['audio']:
        expected.add('soundtrack')
    if set(elements) - expected:
        raise ValueError('Added layers cannot be represented by this Vibe timeline. Keep this draft open and remove unsupported layers before importing.')
    for i, clip in enumerate(plan['clips']):
        e, caption = elements.get(f'clip-{i}'), elements.get(f'caption-{i}')
        if not e or not caption or e.get('src') != s['sources'][clip['asset_id']]:
            raise ValueError('Studio changed or removed a source/layer. Reopen from the Vibe plan.')
        if len(caption['text']) > 500:
            raise ValueError('Keep each caption within 500 characters before importing.')
        start, length, source = (float(e.get(k, 'nan')) for k in ('data-start', 'data-duration', 'data-media-start'))
        if not all(math.isfinite(n) and n >= 0 for n in (start, length, source)) or length <= 0:
            raise ValueError('Studio contains invalid timing.')
        fit = dict(part.split(':', 1) for part in e.get('style', '').split(';') if ':' in part).get('object-fit', 'contain').strip()
        clip.update(start=source, end=source + length, caption=caption['text'], fit=fit)
        timed.append((start, i, clip))
    timed.sort(key=lambda row: (row[0], row[1]))
    position = 0.0
    for start, _, clip in timed:
        if abs(start - position) > .05:
            raise ValueError('Studio timeline has gaps or overlapping clips. Arrange sequential cuts before importing.')
        position += clip['end'] - clip['start']
    plan['clips'] = [clip for _, _, clip in timed]
    if plan['audio']:
        a = elements.get('soundtrack', {})
        original = s['plan']['audio']
        if (a.get('src') != s['sources'][original['asset_id']] or float(a.get('data-start', 'nan')) != 0
            or float(a.get('data-media-start', 'nan')) != original['start']
            or float(a.get('data-duration', 'nan')) != min(sum(c['render_duration'] for c in s['plan']['clips']), original['end']-original['start'])):
            raise ValueError('Soundtrack edits are unsupported. Keep the original audio placement before importing.')
    for layer in plan.get('layers', []):
        e = elements.get('layer-' + layer['id'])
        if not e or ('asset_id' in layer and e.get('src') != s['sources'][layer['asset_id']]):
            raise ValueError('Studio removed or replaced a layer source. Reopen from the Vibe plan.')
        layer['at'] = float(e.get('data-start', 'nan'))
        layer['duration'] = float(e.get('data-duration', 'nan'))
        if 'asset_id' in layer:
            layer['start'] = float(e.get('data-media-start', layer['start']))
            if layer['kind'] != 'image':
                layer['end'] = layer['start'] + layer['duration']
            layer['volume'] = float(e.get('data-volume', layer['volume']))
        style = dict(part.split(':', 1) for part in e.get('style', '').split(';') if ':' in part)
        for css, key in [('left', 'x'), ('top', 'y'), ('width', 'width'), ('height', 'height'), ('opacity', 'opacity'), ('z-index', 'z')]:
            if css in style:
                layer[key] = float(style[css].strip().removesuffix('px'))
        if layer['kind'] == 'text':
            layer['text'] = e['text']
    return plan


def operate(root, project_id, body):
    if not isinstance(body, dict) or set(body) != {'token', 'action'}:
        raise ValueError('Supply exactly token and action.')
    s = sessions.get(root, body['token'], 'studio', project_id, allow_stopped=body['action'] == 'close')
    if body['action'] == 'close':
        sessions.close(s)
        return {'closed': True}
    if body['action'] == 'keepalive':
        return {'revision': s['revision']}
    if body['action'] != 'import':
        raise ValueError('Unknown Studio action.')
    with vibe_editor.state(root, readonly=True) as data:
        p = vibe_editor.project(data, project_id)
        for aid, digest in s['hashes'].items():
            path, _, _ = media_library.asset_path(root, p['workspace_id'], aid)
            if projects.digest(path) != digest:
                raise ValueError('Studio source bytes changed. Re-register and reopen this source.')
    result = vibe_editor.propose_plan(root, project_id, {'revision': s['revision'], 'plan': mapped_plan(s)})
    sessions.close(s)
    return result
