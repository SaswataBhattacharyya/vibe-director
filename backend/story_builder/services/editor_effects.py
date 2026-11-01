"""Bounded editor effects; source media is never modified."""
from __future__ import annotations
import math
import subprocess
from pathlib import Path

SHADERS = ('domain-warp', 'ridged-burn', 'whip-pan', 'sdf-iris', 'ripple-waves',
           'gravitational-lens', 'cinematic-zoom', 'chromatic-split', 'glitch',
           'swirl-vortex', 'thermal-distortion', 'flash-through-white', 'cross-warp-morph', 'light-leak')


def number(value, low, high, name):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{name} must be a number.') from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be between {low} and {high}.')
    return value


def validate(clip, original, last=False):
    effect = original.get('effect', {})
    speed = original.get('speed', {})
    transition = original.get('transition', {})
    if not all(isinstance(v, dict) for v in (effect, speed, transition)):
        raise ValueError('Effect, speed and transition must be objects.')
    preset = effect.get('preset', 'none')
    if preset not in {'none', 'cinematic', 'vhs', 'black-white'}:
        raise ValueError('Unknown video filter.')
    clip['effect'] = {'preset': preset, 'strength': number(effect.get('strength', .5), 0, 1, 'Filter strength')}
    a = number(speed.get('start', 1), .25, 4, 'Starting speed')
    b = number(speed.get('end', a), .25, 4, 'Ending speed')
    if not clip['mime'].startswith('video/') and (a != 1 or b != 1):
        raise ValueError('Speed changes apply to video clips; use the hold duration for images.')
    clip['speed'] = {'start': a, 'end': b}
    kind = transition.get('kind', 'cut')
    if kind not in ('cut', 'dissolve', *SHADERS):
        raise ValueError('Unknown transition.')
    if last and kind != 'cut':
        raise ValueError('The last clip cannot transition into another clip.')
    clip['transition'] = {'kind': kind, 'duration': 0 if kind == 'cut' else number(transition.get('duration', .6), .1, 3, 'Transition duration')}
    clip['render_duration'] = duration(clip)


def duration(clip):
    length = clip['end'] - clip['start']
    a, b = clip.get('speed', {}).get('start', 1), clip.get('speed', {}).get('end', 1)
    return length / a if abs(b-a) < 1e-8 else length * math.log(b/a) / (b-a)


def filters(effect):
    p, s = effect['preset'], effect['strength']
    if p == 'cinematic':
        return f'eq=contrast={1+.18*s}:saturation={1-.22*s}:brightness={-.02*s},colorbalance=rs={.04*s}:bs={-.025*s}:rh={.025*s}:bh={-.035*s}'
    if p == 'vhs':
        return f'eq=contrast={1-.12*s}:saturation={1-.3*s},gblur=sigma={.5*s},chromashift=cbh={round(5*s)}:crh={-round(5*s)},noise=alls={round(18*s)}:allf=t,drawgrid=w=iw:h=4:t=1:c=black@{.22*s}'
    if p == 'black-white':
        return f'hue=s={1-s}'
    return 'null'


def preprocess(source, destination, clip, plan, run, folder, env, progress):
    """Conform one approved range, with continuous video time remapping and matched audio."""
    a, b = clip['speed']['start'], clip['speed']['end']
    length, target = clip['end']-clip['start'], duration(clip)
    video = clip['mime'].startswith('video/')
    # FFmpeg atempo is constant per slice; 32 slices approximate the same continuous video ramp.
    slices = 1 if abs(a-b)<1e-8 else 32
    info = subprocess.run(['ffprobe','-v','error','-select_streams','a','-show_entries','stream=index','-of','csv=p=0',str(source)],capture_output=True,text=True,timeout=30,check=True)
    audio = video and bool(info.stdout.strip()) and not plan.get('audio')
    scale = (f'scale={plan["width"]}:{plan["height"]}:force_original_aspect_ratio=decrease,pad={plan["width"]}:{plan["height"]}:(ow-iw)/2:(oh-ih)/2' if clip['fit']=='contain' else f'scale={plan["width"]}:{plan["height"]}:force_original_aspect_ratio=increase,crop={plan["width"]}:{plan["height"]}')
    time_expr = f'(PTS-STARTPTS)/{a}' if slices==1 else f'({length}/{b-a}*log(1+{(b-a)/length}*(PTS-STARTPTS)*TB/{a}))/TB'
    graph = [f'[0:v]trim=duration={length},setpts={time_expr},{scale},setsar=1,{filters(clip["effect"])},fps={plan["fps"]},tpad=stop_mode=clone:stop_duration=1,trim=duration={target},format=yuv420p[v]']
    if audio:
        graph.append(f'[0:a]asplit={slices}'+''.join(f'[a{i}]' for i in range(slices)))
        for i in range(slices):
            start, end = length*i/slices, length*(i+1)/slices
            out = (end-start)/a if slices==1 else length/(b-a)*math.log((a+(b-a)*end/length)/(a+(b-a)*start/length))
            tempo = (end-start)/out
            graph.append(f'[a{i}]atrim=start={start}:end={end},asetpts=PTS-STARTPTS,atempo={tempo},apad,atrim=duration={out}[s{i}]')
        graph.append(''.join(f'[s{i}]' for i in range(slices))+f'concat=n={slices}:v=0:a=1,apad,atrim=duration={target}[sound]')
    args=['ffmpeg','-nostdin','-v','error','-y','-threads','2']
    args += ['-ss',str(clip['start'])] if video else ['-loop','1']
    args += ['-i',str(source),'-filter_complex_threads','1','-filter_complex',';'.join(graph),'-map','[v]']
    args += ['-map','[sound]','-c:a','aac','-ar','48000'] if audio else ['-an']
    args += ['-t',str(target),'-c:v','libx264','-threads','2','-preset','fast','-crf','18',str(destination)]
    run(args,folder,env,progress)
    return target
