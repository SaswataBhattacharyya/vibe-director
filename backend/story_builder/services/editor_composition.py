"""Trusted composition markup shared by CPU export and in-app HyperFrames preview."""
import html
import json


def document(plan, staged, *, processed=None, gsap='gsap.js', shaders='shaders.js'):
    processed = processed or {}
    duration, elements, animations, transitions, scenes = 0.0, [], [], [], []
    has_transitions = any(c['transition']['kind'] != 'cut' for c in plan['clips'])
    for index, clip in enumerate(plan['clips']):
        length = clip['render_duration']
        source_start = clip['start']
        media = staged[clip['asset_id']]
        if index in processed:
            media = processed[index]
            source_start = 0
        attrs = f'id="clip-{index}" class="clip" data-start="{duration}" data-duration="{length}" data-track-index="{index}"'
        src = html.escape(media, quote=True)
        fit = clip['fit']
        if clip['mime'].startswith('video/') or media.endswith(f'effect-{index}.mp4'):
            sound = 'muted' if plan['audio'] else 'data-has-audio="true"'
            element = f'<video {attrs} data-media-start="{source_start}" {sound} playsinline src="{src}" style="object-fit:{fit}"></video>'
        else:
            element = f'<img {attrs} src="{src}" style="object-fit:{fit}"/>'
        if clip['caption']:
            element += f'<div id="caption-{index}" class="clip caption" data-start="{duration}" data-duration="{length}" data-track-index="{index+50}">{html.escape(clip["caption"])}</div>'
        scenes.append(f'scene-{index}')
        elements.append(f'<div id="scene-{index}" class="scene" style="opacity:{1 if index==0 or not has_transitions else 0}">{element}</div>')
        animations.append(f'tl.to({{}}, {{duration:{length}}}, {duration});')
        duration += length
        if index < len(plan['clips'])-1:
            transition = clip['transition']
            duration -= transition['duration']
            transitions.append({'time': duration, 'duration': transition['duration'],
                                **({'shader': transition['kind']} if transition['kind'] not in {'cut', 'dissolve'} else {})})
    shader_script = ''
    if has_transitions:
        shader_script = f'<script src="{html.escape(shaders, quote=True)}"></script>'
        animations.append('HyperShader.init(' + json.dumps({'scenes': scenes, 'transitions': transitions, 'bgColor': '#000'})[:-1] + ',timeline:tl});')
    if plan['audio']:
        audio = plan['audio']
        elements.append(f'<audio id="soundtrack" class="clip" data-start="0" data-duration="{min(duration, audio["end"]-audio["start"])}" data-track-index="100" data-media-start="{audio["start"]}" data-volume="1" src="{html.escape(staged[audio["asset_id"]], quote=True)}"></audio>')
    document = f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#000;width:100%;height:100%;overflow:hidden}}#main{{position:absolute;inset:0}}.scene{{position:absolute;inset:0}}video,img{{position:absolute;inset:0;width:100%;height:100%}}.caption{{position:absolute;left:10%;right:10%;bottom:10%;z-index:2;color:white;text-shadow:0 2px 4px black;font:48px sans-serif;text-align:center;white-space:pre-wrap}}
</style></head><body><div id="main" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="{plan['width']}" data-height="{plan['height']}">{''.join(elements)}</div><script src="{html.escape(gsap, quote=True)}"></script>{shader_script}<script>window.__timelines={{}};const tl=gsap.timeline({{paused:true}});{''.join(animations)}window.__timelines.main=tl;</script></body></html>'''
    return document, duration
