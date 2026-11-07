"""Approved one-operation tasks. Job records remain execution authority."""
import json
import uuid
from pathlib import Path

from . import agent_computer, agent_continuity, agent_editor, agent_graph, agent_transcription, audio_utilities, media_library, projects, video_repertoire
from .agent_task_schema import SCHEMA
from .production_ledger import LedgerConflict, LedgerNotFound, _now, stable_hash
from .storage_paths import generated_root, media_root

AUDIO_OPERATIONS = {'audio.extract_mp3': 'extract_mp3', 'audio.noise_cleanup': 'noise_cleanup',
                    'audio.demucs_stems': 'demucs_stems'}


class AgentTasks:
    def __init__(self, root, ledger):
        self.root, self.ledger = Path(root), ledger
        with ledger._connect() as db:
            db.executescript(SCHEMA)

    @staticmethod
    def _kind(plan):
        if plan['tool_id'] in AUDIO_OPERATIONS:
            return 'audio-utilities'
        return {"video.continuity_last_frame": "continuity-frame", "computer.execute": "agent-computer",
                'audio.transcribe': agent_transcription.KIND, 'editor.prepare_brief': 'vibe-editor'}[plan["tool_id"]]

    def _assets(self, owner, ids, *, extensions=None):
        if not isinstance(ids, list) or not 1 <= len(ids) <= 100 or any(not isinstance(i, str) for i in ids):
            raise ValueError('Select between one and 100 owned media assets.')
        manifest = agent_graph.read_json(self.root, media_root(self.root, owner) / 'assets.json', {'assets': []})
        records = {r['asset_id']: r for r in media_library._shared_records(self.root)
                   if r.get('workspace_id') == owner}
        records.update({r['asset_id']: r for r in manifest['assets'] if r.get('workspace_id') == owner})
        selected = []
        for ident in dict.fromkeys(ids):
            record = records.get(ident)
            if not record or record.get('archived_at'):
                raise ValueError('Selected asset is unavailable in this project.')
            path, _, filename = media_library.asset_path(self.root, owner, ident)
            digest = projects.digest(path)
            if digest != record.get('sha256'):
                raise LedgerConflict('Selected media changed. Review a new plan before running.')
            if Path(filename).suffix.lower() not in (extensions if extensions is not None else audio_utilities.AUDIO_EXTS | audio_utilities.VIDEO_EXTS):
                raise ValueError('Selected media type is not supported by this operation.')
            selected.append({'asset_id': ident, 'sha256': digest, 'filename': filename})
        return selected

    def _plan(self, owner, payload):
        if not isinstance(payload, dict) or set(payload) != {'tool_id', 'asset_ids', 'settings'}:
            raise ValueError('Supply tool_id, asset_ids and settings.')
        if payload['tool_id'] == 'editor.prepare_brief':
            settings = agent_editor.prepare(self.root, owner, payload['settings'])
            ids = list(dict.fromkeys(r['asset_id'] for r in settings['target']['selected_ranges']))
            if payload['asset_ids'] != ids:
                raise ValueError('Use the saved Editor selection for this brief.')
            assets = self._assets(owner, ids, extensions=agent_editor.EXTENSIONS) if ids else []
            scope = 'Prepare a creative brief in the selected Editor session. Both Editor clearances remain required.'
        elif payload['tool_id'] == 'computer.execute':
            if payload['asset_ids'] != []:
                raise ValueError('Computer tasks use the approved project folder, not staged inputs.')
            assets = []
            settings = agent_computer.prepare(self.root, owner, payload['settings'], self.ledger)
            scope = ('Full local access, including files outside this project and network.' if settings['access_mode'] == 'full'
                     else 'Project folder access; unrelated personal files and network are blocked.')
        elif payload['tool_id'] == 'audio.transcribe':
            if payload['settings'] != {} or not isinstance(payload['asset_ids'], list) or len(payload['asset_ids']) != 1:
                raise ValueError('Speech analysis requires one complete audio/video source and empty settings.')
            assets = self._assets(owner, payload['asset_ids'])
            settings, scope = {}, 'Transcribe one complete source on CPU with source-relative timestamps. Review evidence before proposing cuts; preserve original media.'
        elif payload['tool_id'] == 'video.continuity_last_frame':
            if payload['settings'] != {} or not isinstance(payload['asset_ids'], list) or len(payload['asset_ids']) != 1:
                raise ValueError('Last-frame extraction requires one video and empty settings.')
            assets = self._assets(owner, payload['asset_ids'], extensions=audio_utilities.VIDEO_EXTS)
            settings, scope = {}, 'Extract the last frame as a continuity reference; preserve the original video.'
        elif payload['tool_id'] in AUDIO_OPERATIONS:
            operation = AUDIO_OPERATIONS[payload['tool_id']]
            audio_utilities.validate_settings(operation, payload['settings'])
            defaults = {'extract_mp3': {'quality': 2}, 'noise_cleanup': {'model': 'master64', 'dry': 0},
                        'demucs_stems': {'stems': 2, 'device': 'cpu'}}
            settings = {**defaults[operation], **payload['settings']}
            if operation == 'demucs_stems' and settings['device'] != 'cpu':
                raise ValueError('Director stem separation requires CPU; use manual Audio tools for GPU settings.')
            assets = self._assets(owner, payload['asset_ids'], extensions=(audio_utilities.AUDIO_EXTS | audio_utilities.VIDEO_EXTS
                if operation == 'extract_mp3' else audio_utilities.AUDIO_EXTS))
            scope = {'extract_mp3': 'Extract whole assets to MP3; preserve original media.',
                     'noise_cleanup': 'Denoise complete audio sources using GPU admission; preserve original media.',
                     'demucs_stems': 'Separate complete audio sources into stems on CPU; preserve original media.'}[operation]
        else:
            raise ValueError('Unsupported agent task tool.')
        return {'tool_id': payload['tool_id'], 'assets': assets, 'settings': settings,
                'project_id': owner, 'scope': scope}

    def propose(self, owner, payload):
        with projects.locked(self.root):
            agent_graph.resolve_workspace(self.root, owner)
            plan = self._plan(owner, payload)
            task = 'task-' + uuid.uuid4().hex
            with self.ledger._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO agent_tasks VALUES (?,?,?,?,?,?)', (owner, task, 'draft', 1, _now(), _now()))
                db.execute('INSERT INTO agent_task_plans VALUES (?,?,?,?,?)',
                           (owner, task, 1, stable_hash(plan), json.dumps(plan)))
                self._event(db, owner, task, 'proposed', {'revision': 1})
                db.commit()
            return self.get(owner, task)

    def revise(self, owner, task, payload):
        if not isinstance(payload, dict) or set(payload) != {'revision', 'plan_hash', 'proposal'}:
            raise ValueError('Supply the current revision, plan_hash and replacement proposal.')
        with projects.locked(self.root), self.ledger._connect() as db:
            agent_graph.resolve_workspace(self.root, owner)
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, owner, task)
            self._expected(row, {k: payload[k] for k in ('revision', 'plan_hash')})
            if row['status'] not in {'draft', 'approved'}:
                raise LedgerConflict('A started task retains its frozen plan. Create a new task.')
            plan = self._plan(owner, payload['proposal'])
            revision = row['current_revision'] + 1
            db.execute('INSERT INTO agent_task_plans VALUES (?,?,?,?,?)',
                       (owner, task, revision, stable_hash(plan), json.dumps(plan)))
            db.execute('UPDATE agent_tasks SET current_revision=? WHERE project_id=? AND task_id=?', (revision, owner, task))
            self._set(db, owner, task, 'draft', {'revision': revision})
            db.commit()
        return self.get(owner, task)

    @staticmethod
    def _event(db, owner, task, kind, payload):
        sequence = db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM agent_task_events WHERE project_id=? AND task_id=?',
                              (owner, task)).fetchone()[0]
        db.execute('INSERT INTO agent_task_events VALUES (?,?,?,?,?,?)',
                   (owner, task, sequence, kind, json.dumps(payload), _now()))

    @staticmethod
    def _row(db, owner, task):
        row = db.execute('SELECT t.*,p.plan_hash,p.plan_json FROM agent_tasks t JOIN agent_task_plans p '
                         'ON p.project_id=t.project_id AND p.task_id=t.task_id AND p.revision=t.current_revision '
                         'WHERE t.project_id=? AND t.task_id=?', (owner, task)).fetchone()
        if row is None:
            raise LedgerNotFound('Task not found in this project.')
        if stable_hash(json.loads(row['plan_json'])) != row['plan_hash']:
            raise LedgerConflict('Stored plan integrity check failed.')
        return dict(row)

    def get(self, owner, task):
        agent_graph.resolve_workspace(self.root, owner)
        with self.ledger._connect() as db:
            row = self._row(db, owner, task)
            row['plan'] = json.loads(row.pop('plan_json'))
            call = db.execute('SELECT invocation_id,job_id,state FROM agent_invocations WHERE project_id=? AND task_id=? AND revision=?',
                              (owner, task, row['current_revision'])).fetchone()
            row['invocation'] = dict(call) if call else None
            row['events'] = [dict(e) for e in db.execute('SELECT sequence,event_type,payload_json,created_at FROM agent_task_events '
                                                       'WHERE project_id=? AND task_id=? ORDER BY sequence', (owner, task))]
        return row

    def list(self, owner):
        agent_graph.resolve_workspace(self.root, owner)
        with self.ledger._connect() as db:
            ids = [r[0] for r in db.execute('SELECT task_id FROM agent_tasks WHERE project_id=? ORDER BY created_at DESC LIMIT 50', (owner,))]
        return {'tasks': [self.get(owner, ident) for ident in ids]}

    def speech_evidence(self, owner, assets):
        """Only completed, correlated jobs for the current source bytes inform chat."""
        selected = {a['asset_id']: a['sha256'] for a in assets}
        evidence, seen = [], set()
        for row in self.list(owner)['tasks'] if selected else []:
            plan, invocation = row['plan'], row['invocation']
            if plan['tool_id'] != 'audio.transcribe' or not invocation or not invocation['job_id']:
                continue
            source = plan['assets'][0]
            if source['asset_id'] in seen or selected.get(source['asset_id']) != source['sha256']:
                continue
            job = video_repertoire.read_job(agent_transcription.KIND, invocation['job_id'])
            self._validate_job(row, job)
            if job['status'] != 'completed':
                continue
            result = job.get('result') or {}
            if result.get('workspace_id') != owner:
                raise LedgerConflict('Transcript belongs to another project.')
            report = agent_transcription.report(result.get('transcript'), source)
            evidence.append({'task_id': row['task_id'], 'job_id': job['job_id'], **source,
                'report': report[:16000], 'truncated': len(report) > 16000})
            seen.add(source['asset_id'])
            if len(evidence) == 3:
                break
        return evidence

    def transcript(self, owner, task):
        """Return complete timed evidence only after checking its current owned bytes."""
        row = self.get(owner, task)
        if row['plan']['tool_id'] != 'audio.transcribe' or not row['invocation'] or not row['invocation']['job_id']:
            raise ValueError('Choose a completed speech analysis task.')
        source = row['plan']['assets'][0]
        current = self._assets(owner, [source['asset_id']])[0]
        if current['sha256'] != source['sha256']:
            raise LedgerConflict('Analyzed source changed. Analyze the current bytes before cutting.')
        job = video_repertoire.read_job(agent_transcription.KIND, row['invocation']['job_id'])
        self._validate_job(row, job)
        result = job.get('result') or {}
        if job['status'] != 'completed' or result.get('workspace_id') != owner:
            raise ValueError('Speech analysis has no completed evidence for this project.')
        transcript = result.get('transcript')
        agent_transcription.validate(transcript, source)
        return {'task_id': task, 'job_id': job['job_id'], **source, 'transcript': transcript}

    @staticmethod
    def _expected(row, payload):
        if not isinstance(payload, dict) or set(payload) != {'revision', 'plan_hash'}:
            raise ValueError('Supply the exact revision and plan_hash.')
        if type(payload['revision']) is not int or (payload['revision'], payload['plan_hash']) != (row['current_revision'], row['plan_hash']):
            raise LedgerConflict('Plan changed. Review the current revision.')

    def _check_inputs(self, owner, plan):
        if plan['tool_id'] == 'computer.execute':
            agent_computer.validate(self.root, owner, plan['settings'])
        elif plan['tool_id'] == 'editor.prepare_brief':
            settings = plan['settings']
            if agent_editor.prepare(self.root, owner, {k: settings[k] for k in ('instruction', 'target')}) != settings:
                raise LedgerConflict('Editor context changed. Propose a new plan.')
            if plan['assets'] and self._assets(owner, [a['asset_id'] for a in plan['assets']], extensions=agent_editor.EXTENSIONS) != plan['assets']:
                raise LedgerConflict('Editor media changed. Propose a new plan.')
        elif self._assets(owner, [a['asset_id'] for a in plan['assets']]) != plan['assets']:
            raise LedgerConflict('Inputs changed. Propose a new plan.')

    def approve(self, owner, task, payload):
        with projects.locked(self.root), self.ledger._connect() as db:
            agent_graph.resolve_workspace(self.root, owner)
            db.execute('BEGIN IMMEDIATE')
            row = self._row(db, owner, task)
            self._expected(row, payload)
            if row['status'] not in {'draft', 'approved'}:
                raise LedgerConflict('Only an unstarted task can be approved.')
            plan = json.loads(row['plan_json'])
            self._check_inputs(owner, plan)
            db.execute('INSERT OR IGNORE INTO agent_task_approvals VALUES (?,?,?,?,?)',
                       (owner, task, row['current_revision'], row['plan_hash'], _now()))
            if row['status'] != 'approved':
                self._set(db, owner, task, 'approved')
            db.commit()
        return self.get(owner, task)

    def _set(self, db, owner, task, state, payload=None):
        db.execute('UPDATE agent_tasks SET status=?,updated_at=? WHERE project_id=? AND task_id=?', (state, _now(), owner, task))
        self._event(db, owner, task, state, payload or {})

    def _map_job(self, owner, task, invocation, job):
        with self.ledger._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE agent_invocations SET job_id=?,state=? WHERE project_id=? AND task_id=? AND invocation_id=?',
                       (job['job_id'], 'submitted', owner, task, invocation))
            self._event(db, owner, task, 'job_created', {'job_id': job['job_id']})
            db.commit()

    def _find_job(self, owner, invocation, kind="audio-utilities"):
        matches = []
        for path in (self.root / 'services/media/jobs' / kind).glob('*/job.json'):
            job = agent_graph.read_json(self.root, path)
            request = job.get('request', {})
            if request.get('workspace_id') == owner and request.get('agent_invocation_id') == invocation:
                matches.append(job)
        if len(matches) > 1:
            raise LedgerConflict('Multiple jobs found for one invocation; manual reconciliation required.')
        return matches[0] if matches else None

    @staticmethod
    def _validate_job(row, job):
        request, plan = job.get('request', {}), row['plan']
        if plan['tool_id'] == 'editor.prepare_brief':
            if (request.get('workspace_id') != row['project_id']
                    or request.get('agent_invocation_id') != row['invocation']['invocation_id']
                    or row['invocation']['job_id'] and row['invocation']['job_id'] != job['job_id']):
                raise LedgerConflict('Editor invocation does not match its frozen job.')
            agent_editor.validate_job(row, job)
            return
        inputs = request.get('inputs', [])
        if (request.get('workspace_id') != row['project_id']
                or request.get('agent_invocation_id') != row['invocation']['invocation_id']
                or request.get('operation') != {**AUDIO_OPERATIONS, 'audio.transcribe': 'transcribe', 'video.continuity_last_frame': 'last_frame', 'computer.execute': 'computer'}[plan['tool_id']] or request.get('settings') != plan['settings']
                or [(i.get('asset_id'), i.get('sha256')) for i in inputs] != [(a['asset_id'], a['sha256']) for a in plan['assets']]
                or row['invocation']['job_id'] and row['invocation']['job_id'] != job['job_id']):
            raise LedgerConflict('Frozen job does not match the approved invocation.')

    def run(self, owner, task, payload):
        # The same cross-process lock guards project switching and job allocation.
        # A crashed runner releases it; frozen correlation resolves acknowledgment loss.
        with projects.locked(self.root):
            row = self.get(owner, task)
            self._expected(row, payload)
            if row['status'] in {'completed', 'cancelled', 'failed'}:
                return row
            with self.ledger._connect() as db:
                approved = db.execute('SELECT 1 FROM agent_task_approvals WHERE project_id=? AND task_id=? AND revision=? AND plan_hash=?',
                                      (owner, task, row['current_revision'], row['plan_hash'])).fetchone()
                if not approved:
                    raise LedgerConflict('Approve the exact plan before running.')
                db.execute('BEGIN IMMEDIATE')
                invocation = row['invocation']['invocation_id'] if row['invocation'] else 'call-' + uuid.uuid4().hex
                db.execute('INSERT OR IGNORE INTO agent_invocations VALUES (?,?,?,?,?,?,?)',
                           (owner, task, row['current_revision'], row['plan_hash'], invocation, None, 'submitting'))
                if row['status'] == 'approved':
                    self._set(db, owner, task, 'submitting')
                db.commit()
            job = self._find_job(owner, invocation, self._kind(row["plan"]))
            if row['invocation'] and row['invocation']['job_id'] and job is None:
                raise LedgerConflict('Mapped job is missing; do not create a replacement.')
            if job:
                current = self.get(owner, task)
                self._validate_job(current, job)
                if not row['invocation'] or not row['invocation']['job_id']:
                    self._map_job(owner, task, invocation, job)
                # Queue recovery owns dispatch. A retry never restarts a failed/cancelled job.
                return self._observe(owner, task, job)
            try:
                if (generated_root(self.root, owner) / 'utility_inputs' / ('stage-' + invocation)).exists():
                    raise LedgerConflict('Unclaimed staged input remains from an interrupted submission. Cancel this task and propose a new plan; retained inputs will not be deleted automatically.')
                plan = row['plan']
                self._check_inputs(owner, plan)
                created = lambda job: self._map_job(owner, task, invocation, job)
                if plan['tool_id'] == 'editor.prepare_brief':
                    job = agent_editor.submit(self.root, owner, plan, invocation, created)
                elif plan['tool_id'] == 'computer.execute':
                    job = agent_computer.submit(self.root, owner, plan['settings'], invocation, created)
                elif plan['tool_id'] == 'audio.transcribe':
                    job = agent_transcription.submit(self.root, owner, plan['assets'], invocation, created)
                elif plan['tool_id'] == 'video.continuity_last_frame':
                    job = agent_continuity.submit(self.root, owner, plan['assets'], invocation, created)
                else:
                    job = audio_utilities.submit(self.root, owner,
                        {'operation': AUDIO_OPERATIONS[plan['tool_id']], 'asset_ids': [a['asset_id'] for a in plan['assets']], 'settings': plan['settings']},
                        invocation_id=invocation, expected_hashes={a['asset_id']: a['sha256'] for a in plan['assets']},
                        on_created=created)
            except Exception:
                with self.ledger._connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    self._set(db, owner, task, 'recovery_required')
                    db.commit()
                raise
            return self._observe(owner, task, job)

    def _observe(self, owner, task, job):
        state = job['status']
        outputs = []
        report = None
        plan = self.get(owner, task)['plan']
        if state == 'completed' and plan['tool_id'] == 'editor.prepare_brief':
            result = job.get('result') or {}
            if result.get('pending_clearance') != 'brief' or result.get('revision') != plan['settings']['target']['expected_revision'] + 1:
                raise LedgerConflict('Editor job has no verified brief clearance result.')
            report = 'Creative brief prepared. Review clearance 1 in Vibe Editor; no render was authorized.'
        elif state == 'completed' and plan['tool_id'] == 'audio.transcribe':
            result = job.get('result') or {}
            if result.get('workspace_id') != owner:
                raise LedgerConflict('Transcript belongs to another project.')
            report = agent_transcription.report(result.get('transcript'), plan['assets'][0])
        elif state == 'completed' and self._kind(plan) == agent_computer.KIND:
            result = job.get('result') or {}
            report = result.get('report')
            if result.get('workspace_id') != owner or not isinstance(report, str) or len(report.encode()) > 64000:
                raise LedgerConflict('Completed computer task has no valid report.')
        elif state == 'completed':
            result = job.get('result') or {}
            outputs = result.get('assets') if isinstance(result, dict) else None
            if not isinstance(result, dict) or result.get('workspace_id') != owner or not isinstance(outputs, list) or not outputs or any(not isinstance(a, dict) for a in outputs):
                raise LedgerConflict('Completed job has no registered outputs.')
            extensions = ({'.png'} if plan['tool_id'] == 'video.continuity_last_frame' else
                          {'.mp3'} if plan['tool_id'] == 'audio.extract_mp3' else audio_utilities.AUDIO_EXTS)
            for output in outputs:
                verified = self._assets(owner, [output.get('asset_id')], extensions=extensions)[0]
                if verified['sha256'] != output.get('sha256'):
                    raise LedgerConflict('Job output identity could not be verified.')
            outputs = [media_library.public_asset_record(output, owner) for output in outputs]
        elif state not in {'failed', 'cancelled', 'recovery_required', 'interrupted', 'cancel_requested'}:
            state = 'running'
        if state == 'interrupted':
            state = 'recovery_required'
        with self.ledger._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = self._row(db, owner, task)
            if current['status'] != state:
                self._set(db, owner, task, state, {'job_id': job['job_id'], 'asset_ids': [a['asset_id'] for a in outputs]})
            db.execute('UPDATE agent_invocations SET state=? WHERE project_id=? AND task_id=?', (state, owner, task))
            db.commit()
        result = self.get(owner, task)
        result['outputs'] = outputs
        if report is not None:
            result['report'] = report
        result['job_status'] = job['status']
        return result

    def poll(self, owner, task):
        with projects.locked(self.root):
            row = self.get(owner, task)
            if not row['invocation']:
                return row
            if not row['invocation']['job_id']:
                if row['status'] in {'completed', 'cancelled', 'failed'}:
                    return row
                job = self._find_job(owner, row['invocation']['invocation_id'], self._kind(row['plan']))
                if job:
                    self._validate_job(row, job)
                    self._map_job(owner, task, row['invocation']['invocation_id'], job)
                    return self._observe(owner, task, job)
                with self.ledger._connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    if row['status'] != 'recovery_required':
                        self._set(db, owner, task, 'recovery_required', {'reason': 'No job found for saved submission intent.'})
                    db.commit()
                return self.get(owner, task)
            job = video_repertoire.read_job(self._kind(row['plan']), row['invocation']['job_id'])
            self._validate_job(row, job)
            return self._observe(owner, task, job)

    def cancel(self, owner, task):
        with projects.locked(self.root):
            row = self.get(owner, task)
            if row['invocation']:
                job = self._find_job(owner, row['invocation']['invocation_id'], self._kind(row['plan']))
                if job is None and row['invocation']['job_id']:
                    raise LedgerConflict('Mapped job is missing; reconcile it before cancelling.')
                if job:
                    self._validate_job(row, job)
                    if job['status'] in {'queued', 'running', 'cancel_requested'}:
                        job = video_repertoire.cancel_job(self._kind(row['plan']), job['job_id'])
                    return self._observe(owner, task, job)
            with self.ledger._connect() as db:
                db.execute('BEGIN IMMEDIATE')
                if row['status'] != 'cancelled':
                    self._set(db, owner, task, 'cancelled')
                    db.execute('UPDATE agent_invocations SET state=? WHERE project_id=? AND task_id=?', ('cancelled', owner, task))
                db.commit()
            return self.get(owner, task)
