"""Service-backed descriptions only. Discovery never authorizes execution."""
import shutil
from . import agent_transcription, audio_utilities, frame_pipeline

_CONTRACTS = {
    'image.generate_next_keyframe': ('Generate one Kontext candidate from the approved take head; owner review is required.', ['image'], 'reviewed_take', 'comfyui', 'unreviewed_candidate'),
    'video.interpolate_keyframes': ('Interpolate an approved continuous-shot take with FILM or RIFE; never interpolate across cuts.', ['image'], 'reviewed_take', 'comfyui', 'verified_frame_sequence'),
    'video.export_frame_sequence': ('Export a completed reviewed sequence as silent MP4 and lossless FFV1.', ['image'], 'reviewed_take', 'ffmpeg', 'registered_video'),
    'editor.prepare_clip_join': ('Prepare a Kdenlive join preview from completed overlap evidence; never approve or render the final cut.', ['video'], 'saved_editor_selection', 'kdenlive_mcp', 'pending_editor_join'),
    'video.compare_clip_overlap': ('Compare two ordered videos for moving tail/head overlap; evidence only, no edits.', ['video'], 'bounded_tail_head', 'ffmpeg', 'overlap_evidence'),
    'audio.extract_mp3': ('Extract audio from complete audio/video sources into MP3 files.',
                         ['audio', 'video'], 'whole_source', 'ffmpeg', 'registered_audio'),
    'video.continuity_last_frame': ('Extract one video’s final frame as a continuity reference.',
                                    ['video'], 'whole_source', 'ffmpeg', 'registered_image'),
    'editor.prepare_brief': ('Prepare an edit brief for review; cannot analyze speech, approve cuts or render.',
                             ['audio', 'video', 'image'], 'saved_editor_selection', 'reasoning_provider', 'pending_editor_brief'),
    'computer.execute': ('Run an explicitly approved coding, terminal or filesystem task.',
                         [], 'explicit_access_mode', 'codex_cli', 'verified_report'),
    'audio.transcribe': ('Transcribe one complete source on CPU with timed speech and confidence evidence; review required before cuts.',
                         ['audio', 'video'], 'whole_source', 'video-audio-analyzer-peav:dev', 'timed_transcript'),
    'audio.noise_cleanup': ('Denoise audio using the installed denoiser. Requires GPU admission at execution.',
                           ['audio'], 'whole_source', 'story-audio-denoiser', 'registered_audio'),
    'audio.demucs_stems': ('Separate vocals and accompaniment from audio using Demucs on CPU.',
                         ['audio'], 'whole_source', 'story-audio-demucs', 'registered_audio'),
}


def tools() -> dict:
    ready = bool(shutil.which('ffmpeg'))
    asset_ids = {'type': 'array', 'minItems': 1, 'maxItems': 100, 'items': {'type': 'string', 'minLength': 1}}
    rows = [
        {'id': 'audio.extract_mp3', 'effect': 'submit', 'input_schema': {
            'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': asset_ids, 'settings': {'type': 'object', 'additionalProperties': False,
                'properties': {'quality': {'type': 'integer', 'minimum': 0, 'maximum': 9, 'default': 2}}}}}},
        {'id': 'video.continuity_last_frame', 'effect': 'submit', 'input_schema': {
            'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': {**asset_ids, 'maxItems': 1},
                'settings': {'type': 'object', 'additionalProperties': False, 'properties': {}}}}},
    ]
    rows.append({'id': 'video.compare_clip_overlap', 'effect': 'submit', 'input_schema': {
        'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
        'properties': {'asset_ids': {**asset_ids, 'minItems': 2, 'maxItems': 2, 'uniqueItems': True},
            'settings': {'type': 'object', 'additionalProperties': False, 'properties': {
                'window_seconds': {'type': 'number', 'minimum': .5, 'maximum': 10, 'default': 3}}}}}})
    ready = ready and bool(shutil.which('ffprobe'))
    for row in rows:
        row.update(status='available' if ready else 'blocked', execution_enabled=ready)
        if not ready:
            row['reason'] = 'ffmpeg is unavailable.' if not shutil.which('ffmpeg') else 'ffprobe is unavailable.'
    if ready:
        for row in rows:
            row['reason'] = 'Propose a task, approve its exact plan, then run it through the shared task gateway.'
    operations = {row['id']: row for row in audio_utilities.capabilities()['operations']}
    for operation, settings in (
        ('noise_cleanup', {'model': {'enum': ['master64', 'dns64'], 'default': 'master64'},
                           'dry': {'type': 'number', 'minimum': 0, 'maximum': 1, 'default': 0}}),
        ('demucs_stems', {'stems': {'enum': [2, 4, 6], 'default': 2},
                          'device': {'const': 'cpu', 'default': 'cpu'}}),
    ):
        readiness = operations.get(operation, {})
        available = readiness.get('status') == 'available'
        rows.append({'id': 'audio.' + operation, 'effect': 'submit',
            'status': 'available' if available else 'blocked', 'execution_enabled': available,
            'reason': 'Requires exact-plan approval; preserves originals.' if available else readiness.get('reason', 'Audio runtime is unavailable.'),
            'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
                'properties': {'asset_ids': asset_ids, 'settings': {'type': 'object',
                    'additionalProperties': False, 'properties': settings}}}})
    computer = bool(shutil.which('codex'))
    editor_target = {
        'type': 'object', 'additionalProperties': False,
        'required': ['version', 'editor_session_id', 'expected_revision', 'selected_ranges'],
        'properties': {
            'version': {'const': 1}, 'editor_session_id': {'type': 'string'},
            'expected_revision': {'type': 'integer', 'minimum': 0},
            'selected_ranges': {'type': 'array', 'maxItems': 100, 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['asset_id', 'start', 'end'],
                'properties': {'asset_id': {'type': 'string'}, 'start': {'type': 'number'}, 'end': {'type': 'number'}}}},
        },
    }
    from .kdenlive_mcp import capability
    kdenlive = capability()
    rows.append({'id': 'editor.prepare_clip_join', 'effect': 'submit',
        'status': 'available' if kdenlive['ready'] else 'blocked', 'execution_enabled': kdenlive['ready'],
        'reason': kdenlive['message'], 'input_schema': {'type': 'object', 'additionalProperties': False,
            'required': ['asset_ids', 'settings'], 'properties': {'asset_ids': {**asset_ids, 'minItems': 2, 'maxItems': 2},
                'settings': {'type': 'object', 'additionalProperties': False, 'required': ['target', 'comparison_task_id'],
                    'properties': {'target': editor_target, 'comparison_task_id': {'type': 'string'}}}}}})
    rows.append({'id': 'editor.prepare_brief', 'effect': 'submit', 'status': 'available', 'execution_enabled': True,
        'reason': 'Requires a saved Editor session and exact task approval. Prepares clearance 1; never approves or renders.',
        'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': {**asset_ids, 'minItems': 0}, 'settings': {
                'type': 'object', 'additionalProperties': False, 'required': ['instruction', 'target'],
                'properties': {'instruction': {'type': 'string', 'minLength': 1, 'maxLength': 12000},
                    'target': editor_target}}}}})
    rows.append({'id': 'computer.execute', 'effect': 'submit',
        'status': 'available' if computer else 'blocked', 'execution_enabled': computer,
        'reason': 'Requires an open project, explicit access mode and exact-plan approval. Terminal, coding and filesystem; interactive browser control is unavailable.' if computer else 'Codex CLI is unavailable.',
        'input_schema': {'type': 'object', 'additionalProperties': False, 'required': ['asset_ids', 'settings'],
            'properties': {'asset_ids': {'type': 'array', 'maxItems': 0}, 'settings': {
                'type': 'object', 'additionalProperties': False, 'required': ['instruction', 'access_mode', 'skill_refs'],
                'properties': {'instruction': {'type': 'string', 'minLength': 1, 'maxLength': 12000},
                    'access_mode': {'enum': ['project', 'full']},
                    'skill_refs': {'type': 'array', 'maxItems': 6, 'items': {'type': 'string'}}}}}}})
    rows.append({'id': 'audio.transcribe', 'effect': 'submit', **agent_transcription.capability(),
        'input_schema': {'type': 'object', 'additionalProperties': False,
            'required': ['asset_ids', 'settings'], 'properties': {'asset_ids': {**asset_ids, 'maxItems': 1},
                'settings': {'type': 'object', 'additionalProperties': False, 'properties': {}}}}})
    for tool, operation in frame_pipeline.TOOLS.items():
        fields = {'take_id': {'type':'string'}, 'revision': {'type':'integer','minimum':1}}
        fields.update({'prompt':{'type':'string','minLength':1},'seed':{'type':'integer','minimum':0}} if operation == 'next'
            else {'model':{'enum':['film','rife']},'multiplier':{'type':'integer','minimum':2,'maximum':16},
                  'fps':{'type':'number','minimum':1,'maximum':60},'hold':{'type':'number','minimum':0,'maximum':10}} if operation == 'interpolate'
            else {'sequence_job_id':{'type':'string'}})
        rows.append({'id':tool,'effect':'submit','status':'available' if ready else 'blocked',
            'execution_enabled':ready,'reason':'Requires an approved take and exact-plan approval. Backend model readiness is checked at execution.',
            'input_schema':{'type':'object','additionalProperties':False,'required':['asset_ids','settings'],
                'properties':{'asset_ids':asset_ids,'settings':{'type':'object','additionalProperties':False,
                    'required':list(fields),'properties':fields}}}})
    for row in rows:
        description, media, scope, runtime, result = _CONTRACTS[row['id']]
        row.update(description=description, accepted_media=media, scope=scope, runtime=runtime,
                   approval='exact_plan', result_kind=result)
    from .agent_native_tools import catalogue
    from .agent_generation_tools import catalogue as generation_catalogue
    return {'tools': rows + catalogue() + generation_catalogue()}
