"""Bounded CPU suffix/prefix comparison. Scores are evidence, never cut approval."""
import json
import math
import subprocess
from fractions import Fraction

SIZE = 16


def settings(value):
    if not isinstance(value, dict) or set(value) - {'window_seconds'}:
        raise ValueError('Overlap settings accept only window_seconds (0.5–10).')
    window = value.get('window_seconds', 3)
    if type(window) not in (int, float) or not math.isfinite(window) or not .5 <= window <= 10:
        raise ValueError('Choose an overlap window between 0.5 and 10 seconds.')
    return {'window_seconds': window}


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
                            check=True, capture_output=True, text=True, timeout=30)
    value = json.loads(result.stdout)
    video = next((s for s in value.get('streams', []) if s['codec_type'] == 'video'), None)
    if video is None:
        raise ValueError('Overlap analysis requires two video sources.')
    duration = float(video.get('duration') or value.get('format', {}).get('duration') or 0)
    rate = Fraction(video.get('avg_frame_rate') or video.get('r_frame_rate') or '0/1')
    if not math.isfinite(duration) or duration <= 0 or not 0 < rate <= 240:
        raise ValueError('Video duration or frame rate is unavailable or unsupported.')
    return {'duration': duration, 'fps': str(rate), 'width': video['width'], 'height': video['height']}


def frames(path, start, duration, fps):
    # Output is capped to 601 tiny frames regardless of source dimensions/duration.
    result = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-ss', str(start), '-i', str(path),
        '-t', str(duration), '-an', '-vf', f'fps={fps},scale={SIZE}:{SIZE},format=gray',
        '-frames:v', '601', '-f', 'rawvideo', 'pipe:1'], check=True, capture_output=True, timeout=60)
    data = result.stdout
    return [data[i:i+SIZE*SIZE] for i in range(0, len(data), SIZE*SIZE) if len(data[i:i+SIZE*SIZE]) == SIZE*SIZE]


def dhash(frame):
    bits = 0
    for y in range(0, 16, 2):
        for x in range(0, 14, 2):
            bits = (bits << 1) | (frame[y*16+x] > frame[y*16+x+2])
    return bits


def similarity(a, b):
    count = len(a)
    ma, mb = sum(a)/count, sum(b)/count
    va = sum((v-ma)**2 for v in a)/count
    vb = sum((v-mb)**2 for v in b)/count
    covariance = sum((x-ma)*(y-mb) for x, y in zip(a, b))/count
    return ((2*ma*mb+6.5025)*(2*covariance+58.5225))/((ma*ma+mb*mb+6.5025)*(va+vb+58.5225))


def motion(rows):
    if len(rows) < 2:
        return 0
    return sum(sum(abs(x-y) >= 4 for x, y in zip(a, b))/len(a)
               for a, b in zip(rows, rows[1:]))/(len(rows)-1)


def align(a, b, fps):
    minimum = max(4, math.ceil(.25*fps))
    limit = min(len(a), len(b))
    base = {'status': 'inconclusive', 'score': None, 'overlap_seconds': None,
            'reason': 'Too few distinct moving frames to establish repeated footage.'}
    if limit < minimum or min(motion(a), motion(b)) < .015:
        return base
    ha, hb = [dhash(row) for row in a], [dhash(row) for row in b]
    candidates = []
    for n in range(minimum, limit+1):
        distance = sum((x^y).bit_count() for x, y in zip(ha[-n:], hb[:n]))/(56*n)
        candidates.append((distance, n))
    ranked = sorted(candidates)[:5]
    checked = []
    for distance, n in ranked:
        scores = [similarity(x, y) for x, y in zip(a[-n:], b[:n])]
        checked.append((sum(scores)/n, distance, n, min(scores)))
    score, distance, n, worst = max(checked)
    others = [d for d, count in candidates if abs(count-n) > max(2, fps*.25)]
    distinctive = not others or min(others)-distance > .015
    if score < .9 or distance > .12:
        return {**base, 'status': 'no_match', 'score': round(score, 4),
                'reason': 'No consistent moving suffix/prefix match was found within the searched windows.'}
    if score < .96 or worst < .88 or not distinctive or min(motion(a[-n:]), motion(b[:n])) < .015:
        return {**base, 'score': round(score, 4),
                'reason': 'Similar frames exist, but motion or alignment is ambiguous. Review manually; no trim recommended.'}
    return {'status': 'match', 'score': round(score, 4), 'overlap_seconds': n/fps,
            'reason': 'A distinct, temporally ordered moving sequence matches across the join.',
            'sample_count': n, 'hash_distance': round(distance, 4)}


def compare(first, second, options=None):
    options = settings(options or {})
    sources = [probe(path) for path in (first, second)]
    # A bounded common time grid handles unequal rates without equating frame indices.
    fps = min(60, max(12, math.ceil(max(float(Fraction(s['fps'])) for s in sources))))
    window = options['window_seconds']
    lengths = [min(window, s['duration']) for s in sources]
    offset = max(0, sources[0]['duration']-lengths[0])
    a = frames(first, offset, lengths[0], fps)
    b = frames(second, 0, lengths[1], fps)
    result = align(a, b, fps)
    overlap = result['overlap_seconds']
    return {'version': 1, **result, 'sources': sources, 'settings': options, 'sample_fps': fps,
        'timing_uncertainty_seconds': 1/fps, 'a_window_start': offset,
        'estimated_duplicate_frames': round(overlap*float(Fraction(sources[1]['fps']))) if overlap else None,
        'suggested_ranges': [{'start': 0, 'end': sources[0]['duration']},
                             {'start': overlap, 'end': sources[1]['duration']}] if overlap and overlap < sources[1]['duration'] else None,
        'evidence': [{'a_seconds': sources[0]['duration']-overlap+i/fps, 'b_seconds': i/fps}
                     for i in sorted({0, result.get('sample_count', 1)//2, result.get('sample_count', 1)-1})] if overlap else [],
        'limitations': 'Similarity score is not a probability. Timing is on a common sampling grid; review playback before approving cuts.'}
