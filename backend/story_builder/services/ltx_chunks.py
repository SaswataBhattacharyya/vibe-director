"""Bounded LTX staging/joining adapted from ricky/h3_ltx/run_chunked_flow.py.

The existing production worker owns submissions, monitoring and recovery.
"""
from __future__ import annotations
from story_builder.services.storage_paths import intermediate_root
import os
import re
import subprocess
from pathlib import Path
import numpy as np
from story_builder.services.t2v_pipeline import digest, probe as media_probe, video_stream
from story_builder.services.minimax_h3_t2v import final_dimensions


def probe(path):
    info = media_probe(path)
    stream = video_stream(info, require_audio=False)
    return info, stream, int(stream['nb_read_frames'])


def windows(n, size, overlap, cuts):
    if not (size >= 17 and 0 < overlap < size // 2):
        raise ValueError('Invalid LTX chunk size/overlap')
    if cuts != sorted(set(cuts)) or not all(0 < c < n for c in cuts):
        raise ValueError('Invalid scene cut boundaries')
    result = []
    for shot, (lo, hi) in enumerate(zip([0] + cuts, cuts + [n])):
        start = lo
        while start < hi:
            end = min(start + size, hi)
            result.append(dict(shot=shot, start=start, end=end, frames=end-start, padded_frames=end-start+(-(end-start-1)) % 8))
            if end == hi:
                break
            start = end - overlap
    return result


def detect_cuts(source, n):
    p = subprocess.run([os.environ.get('FFMPEG', 'ffmpeg'), '-nostdin', '-hide_banner', '-i', str(source), '-vf', "select='gt(scene,0.35)',showinfo", '-an', '-f', 'null', '-'], capture_output=True, text=True, timeout=600, check=True)
    return sorted(set(round(float(t)*24) for t in re.findall(r'pts_time:([0-9.]+)', p.stderr) if 0 < round(float(t)*24) < n))


def split_input(source, chunk, dest):
    # Lossless bounded input; explicit silence is only for the LTX audio latent.
    pad = chunk['padded_frames'] - chunk['frames']
    begin, end = chunk['start']/24, chunk['end']/24
    audio = any(x['codec_type'] == 'audio' for x in probe(source)[0]['streams'])
    cmd = [os.environ.get('FFMPEG', 'ffmpeg'), '-nostdin', '-v', 'error', '-y', '-threads', '2', '-i', str(source)]
    if not audio:
        cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
    duration = chunk['padded_frames']/24
    cmd += ['-map', '0:v:0', '-map', '0:a:0' if audio else '1:a:0', '-vf', f"trim=start_frame={chunk['start']}:end_frame={chunk['end']},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop={pad}", '-af', f'atrim=start={begin}:end={end},asetpts=PTS-STARTPTS,apad=whole_dur={duration},atrim=duration={duration}', '-frames:v', str(chunk['padded_frames']), '-c:v', 'ffv1', '-threads', '2', '-c:a', 'pcm_s16le', str(dest)]
    subprocess.run(cmd, capture_output=True, timeout=600, check=True)
    if probe(dest)[2] != chunk['padded_frames']:
        raise ValueError('Staged LTX chunk frame count mismatch')


def join_chunks(chunks, output, width, height):
    """Stream RGB frames, retaining only the next overlap, never whole clips."""
    frame_bytes = width * height * 3
    enc = subprocess.Popen([os.environ.get('FFMPEG', 'ffmpeg'), '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}', '-r', '24', '-i', '-', '-an', '-c:v', 'libx264', '-threads', '2', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)], stdin=subprocess.PIPE)
    pending = []
    written = 0
    try:
        for i, c in enumerate(chunks):
            incoming = len(pending)
            following = chunks[i+1] if i+1 < len(chunks) else None
            outgoing = c['end']-following['start'] if following and following['shot'] == c['shot'] else 0
            if incoming + outgoing > c['frames']:
                raise ValueError('Overlap regions must not intersect')
            dec = subprocess.Popen([os.environ.get('FFMPEG', 'ffmpeg'), '-nostdin', '-v', 'error', '-threads', '2', '-i', c['refined'], '-map', '0:v:0', '-frames:v', str(c['frames']), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '2', '-'], stdout=subprocess.PIPE)
            tail = []
            try:
                for j in range(c['frames']):
                    data = dec.stdout.read(frame_bytes)
                    if len(data) != frame_bytes:
                        raise ValueError('Refinement shorter than requested window')
                    if j < incoming:
                        alpha = (j+1)/(incoming+1)
                        a = np.frombuffer(pending[j], np.uint8)
                        b = np.frombuffer(data, np.uint8)
                        data = np.rint(a.astype(np.float32)*(1-alpha)+b.astype(np.float32)*alpha).astype(np.uint8).tobytes()
                    if j >= c['frames']-outgoing:
                        tail.append(data)
                    else:
                        enc.stdin.write(data)
                        written += 1
                if dec.wait(timeout=120) != 0:
                    raise ValueError('Chunk decoding failed')
            finally:
                dec.stdout.close()
                if dec.poll() is None:
                    dec.terminate()
                    try:
                        dec.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        dec.kill()
                        dec.wait(timeout=10)
            pending = tail
        if pending:
            raise ValueError('Unjoined LTX overlap frames')
        enc.stdin.close()
        code = enc.wait(timeout=180)
    finally:
        # A failed decoder or encoder must not leave an FFmpeg child behind.
        # Preserve the original exception if the pipe has already broken.
        try:
            enc.stdin.close()
        except BrokenPipeError:
            pass
        if enc.poll() is None:
            enc.terminate()
            try:
                enc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                enc.kill()
                enc.wait(timeout=10)
    if code != 0:
        raise ValueError('LTX join encoding failed')
    if probe(output)[2] != written:
        raise ValueError('Joined LTX frame count mismatch')
    return written



def plan_chunks(source, count):
    plan = windows(count, 65, 16, detect_cuts(source, count))
    # Preserve hard cuts, padding very short shots rather than crossing a cut.
    for window in plan:
        window['padded_frames'] = max(17, window['padded_frames'])
    return plan


def collect_chunk(take, source, *, data_root, joined_path):
    """Checkpoint intermediate chunks; join only after the last validated chunk."""
    pipeline = take['pipeline']
    plan = pipeline['ltx_chunks']
    index = pipeline['ltx_chunk_index']
    window = plan[index]
    root = Path(data_root).resolve()
    width, height = final_dimensions(take['input_snapshot']['resolution_preset'],
                                      take['input_snapshot']['aspect_ratio'])
    _, stream, frames = probe(source)
    if (stream['width'], stream['height']) != (width, height) or frames < window['padded_frames']:
        raise ValueError('LTX chunk dimensions/frame count mismatch')
    source_hash = digest(source)
    folder = intermediate_root(root, take['project_id'], 'chunks') / take['job_id']
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f'{index:04d}_{source_hash}.mp4'
    if not target.exists():
        import shutil
        import uuid
        staged = folder / f'.{uuid.uuid4().hex}.tmp'
        shutil.copy2(source, staged)
        os.replace(staged, target)
    record = {'pipeline_chunk': True, 'index': index, 'sha256': source_hash,
              'relative_path': target.relative_to(root).as_posix(),
              'prompt_id': take.get('prompt_id'), 'kind': 'video'}
    completed = pipeline.get('ltx_chunk_outputs', [])
    if len(completed) != index:
        raise ValueError('LTX checkpoint order mismatch')
    if index + 1 < len(plan):
        return record
    chunks = []
    for position, saved in enumerate(completed + [record]):
        if saved['index'] != position:
            raise ValueError('LTX chunk order changed')
        path = (root / saved['relative_path']).resolve()
        path.relative_to(folder.resolve())
        if not path.is_file() or digest(path) != saved['sha256']:
            raise ValueError('Saved LTX chunk is missing or changed')
        chunks.append({**plan[position], 'refined': str(path)})
    written = join_chunks(chunks, joined_path, width, height)
    if written != plan[-1]['end']:
        raise ValueError('Joined LTX duration differs from the original')
    return None
