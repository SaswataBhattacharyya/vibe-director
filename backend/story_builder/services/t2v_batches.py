"""Sequential T2V manifests; the existing production worker owns all GPU execution."""
from __future__ import annotations
from story_builder.services.storage_paths import generated_root

import fcntl
import hashlib
import json
import re
import uuid
from contextlib import contextmanager

from story_builder.services.isolated_video_contract import EXPECTED_GRAPH_SHA256
from story_builder.services.isolated_video_jobs import _identifier
from story_builder.services.production_ledger import LedgerConflict, LedgerNotFound

HEADER = re.compile(r'^#prompt\s+([A-Za-z0-9][A-Za-z0-9_-]{0,63}):\s*time=\s*(\d+(?:\.\d+)?)sec,\s*AR=\s*(\d+:\d+),\s*(?:Quality=\s*(\d+(?:\.\d+)?)|Q1=\s*(\d+(?:\.\d+)?)\s*,?\s*Q2=\s*(\d+(?:\.\d+)?))\s*$', re.MULTILINE)


def parse_batch(source):
    if not isinstance(source, str) or not source.strip() or len(source.encode('utf-8')) > 1_000_000:
        raise ValueError('Provide a nonempty batch file smaller than 1 MB.')
    source = source.lstrip('\ufeff').strip()
    if source.startswith(('{', '[')):
        raw = json.loads(source)
        if isinstance(raw, dict):
            if set(raw) != {'prompts'}:
                raise ValueError('JSON must contain only a prompts array.')
            raw = raw['prompts']
    else:
        matches = list(HEADER.finditer(source))
        if not matches or source[:matches[0].start()].strip():
            raise ValueError('Start with #prompt 1: time=15sec, AR=9:16, Q1=0.6 Q2=0.98')
        raw = []
        for index, match in enumerate(matches):
            body = source[match.end():matches[index+1].start() if index+1 < len(matches) else len(source)].strip()
            if not body.startswith('"') or not body.endswith('"'):
                raise ValueError(f'Prompt {index+1}: enclose the prompt in double quotes.')
            prompt = body[1:-1].strip()
            # Invalid headers cannot silently become part of a preceding prompt.
            if re.search(r'^#prompt\b', prompt, re.MULTILINE):
                raise ValueError(f'Prompt {index+1}: malformed following header.')
            qualities = {'Quality': float(match[4])} if match[4] is not None else {'Q1': float(match[5]), 'Q2': float(match[6])}
            raw.append({'id': match[1], 'time': float(match[2]), 'AR': match[3],
                        **qualities, 'prompt': prompt})
    if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
        raise ValueError('A batch must contain 1–100 prompts.')
    seen = set()
    for index, entry in enumerate(raw, 1):
        if not isinstance(entry, dict) or set(entry) not in ({'id', 'time', 'AR', 'Quality', 'prompt'}, {'id', 'time', 'AR', 'Q1', 'Q2', 'prompt'}):
            raise ValueError(f'Prompt {index}: expected id, time, AR, Q1, Q2 and prompt (or legacy Quality instead of Q1/Q2).')
        value = entry['id']
        if type(value) not in (int, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', str(value)):
            raise ValueError('Prompt IDs must be 1–64 letters, digits, hyphens or underscores, starting with a letter or digit.')
        entry['id'] = str(value)
        if entry['id'].casefold() in seen:
            raise ValueError(f"Duplicate prompt ID: {value}. IDs must be unique within the batch (ignoring case).")
        seen.add(entry['id'].casefold())
    return raw


class T2VBatches:
    def __init__(self, jobs):
        self.jobs = jobs
        self.ledger = jobs.ledger
        self.lock_path = self.ledger.path.with_suffix('.t2v-batches.lock')
        with self.ledger._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS t2v_batches (
                batch_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL, manifest_hash TEXT NOT NULL,
                entries_json TEXT NOT NULL, state TEXT NOT NULL, reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workspace_id,idempotency_key))''')

            db.execute("""CREATE TABLE IF NOT EXISTS t2v_batch_output_names (
                workspace_id TEXT NOT NULL, filename TEXT NOT NULL COLLATE NOCASE,
                clip_id TEXT NOT NULL, PRIMARY KEY(workspace_id,filename))""")

    def _legacy_outputs(self, db, workspace_id):
        # Old manifests used content-hash filenames; still recognize their IDs.
        outputs = {}
        for batch in db.execute('SELECT entries_json FROM t2v_batches WHERE workspace_id=? ORDER BY created_at,rowid', (workspace_id,)):
            for entry in json.loads(batch['entries_json']):
                if entry.get('filename') or not entry.get('job_id'):
                    continue
                asset = db.execute('SELECT a.asset_id,a.metadata_json FROM isolated_video_assets a JOIN isolated_video_asset_refs r ON r.asset_id=a.asset_id WHERE r.job_id=?', (entry['job_id'],)).fetchone()
                if asset:
                    metadata = json.loads(asset['metadata_json'])
                    path = self.jobs.media_root / metadata['relative_path'] if self.jobs.media_root is not None else None
                    if path is not None and metadata.get('shared_asset_id'):
                        from .media_library import asset_path
                        try: path, _, _ = asset_path(self.jobs.media_root, workspace_id, metadata['shared_asset_id'])
                        except (ValueError, OSError): path = None
                    if path is not None and path.is_file():
                        outputs[(str(entry['number']) + '.mp4').casefold()] = asset['asset_id']
        return outputs

    def _used_names(self, db, workspace_id):
        names = {r['filename'].casefold() for r in db.execute(
            'SELECT filename FROM t2v_batch_output_names WHERE workspace_id=?', (workspace_id,))}
        names.update(self._legacy_outputs(db, workspace_id))
        if self.jobs.media_root is not None:
            directory = generated_root(self.jobs.media_root, workspace_id)
            if directory.is_dir():
                names.update(p.name.casefold() for p in directory.iterdir())
        return names

    @contextmanager
    def _lock(self):
        with self.lock_path.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def validate(self, source, workspace_id=None):
        entries = []
        for entry in parse_batch(source):
            try:
                result = self.jobs.validate(dict(workflow_id='minimax_h3_t2v_local_v1',
                    workflow_version=2, workflow_sha256=EXPECTED_GRAPH_SHA256,
                    prompt=entry['prompt'], duration_seconds=entry['time'],
                    aspect_ratio=entry['AR'], resolution_preset=entry.get('Q2', entry.get('Quality')),
                    **({'source_resolution_preset': entry['Q1']} if 'Q1' in entry else {}),
                    steps=4, seed=1, references=[]))
            except ValueError as exc:
                raise ValueError(f"Prompt {entry['id']}: {exc}") from exc
            entries.append({'number': entry['id'], 'request': result['normalized_request'],
                            'job_id': None})
        conflicts = []
        if workspace_id is not None:
            workspace_id = _identifier(workspace_id, 'workspace_id')
            with self.ledger._connect() as db:
                used = self._used_names(db, workspace_id)
            conflicts = [e['number'] for e in entries if (e['number'] + '.mp4').casefold() in used]
        return {'entries': entries, 'count': len(entries), 'conflicts': conflicts}

    def _row(self, batch_id):
        with self.ledger._connect() as db:
            row = db.execute('SELECT * FROM t2v_batches WHERE batch_id=?', (batch_id,)).fetchone()
        if row is None:
            raise LedgerNotFound('Batch not found.')
        return dict(row)

    def get(self, batch_id):
        row = self._row(batch_id)
        entries = json.loads(row.pop('entries_json'))
        for entry in entries:
            if entry['job_id']:
                try:
                    entry['job'] = self.jobs.get_job(entry['job_id'])
                except LedgerNotFound:
                    entry['job_missing'] = True
        row['entries'] = entries
        row['completed'] = sum(self._complete(e.get('job', {})) for e in entries)
        return row

    @staticmethod
    def _complete(job):
        return (job.get('status') in {'needs_review', 'accepted'}
                and any(o.get('kind') == 'video' and o.get('available') is not False
                        and o.get('playback_url') for o in job.get('outputs', [])))

    def list(self, workspace_id):
        workspace_id = _identifier(workspace_id, 'workspace_id')
        with self.ledger._connect() as db:
            rows = db.execute('SELECT batch_id FROM t2v_batches WHERE workspace_id=? ORDER BY created_at DESC,rowid DESC LIMIT 30', (workspace_id,)).fetchall()
        return {'batches': [self.get(row['batch_id']) for row in rows]}

    def create(self, workspace_id, key, source, choices=None):
        workspace_id = _identifier(workspace_id, 'workspace_id')
        key = _identifier(key, 'idempotency_key')
        entries = self.validate(source)['entries']
        choices = choices or {}
        if not isinstance(choices, dict) or any(k not in {e['number'] for e in entries} or v not in ('overwrite', 'new_take') for k, v in choices.items()):
            raise ValueError('Invalid filename conflict choices.')
        encoded = json.dumps(entries, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(json.dumps([entries, choices], sort_keys=True).encode()).hexdigest()
        with self._lock(), self.ledger._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM t2v_batches WHERE workspace_id=? AND idempotency_key=?', (workspace_id, key)).fetchone()
            if old:
                if old['manifest_hash'] != digest:
                    # Recover pre-naming starts using their original saved admission keys.
                    previous = json.loads(old['entries_json'])
                    comparable = [{'number': str(e['number']), 'request': e['request'], 'job_id': None} for e in previous]
                    if choices or any('admission_key' in e for e in previous) or comparable != entries:
                        raise LedgerConflict('This batch key already belongs to different prompts.')
                batch_id = old['batch_id']
            else:
                if db.execute("SELECT 1 FROM t2v_batches WHERE workspace_id=? AND state NOT IN ('completed','stopped')", (workspace_id,)).fetchone():
                    raise LedgerConflict('This project already has a batch. Resume or stop it before starting another.')
                batch_id = str(uuid.uuid4())
                used = self._used_names(db, workspace_id)
                legacy_outputs = self._legacy_outputs(db, workspace_id)
                for position, entry in enumerate(entries, 1):
                    filename = entry['number'] + '.mp4'
                    owner = db.execute('SELECT * FROM t2v_batch_output_names WHERE workspace_id=? AND filename=?', (workspace_id, filename)).fetchone()
                    if filename.casefold() in used:
                        decision = choices.get(entry['number'])
                        if decision is None:
                            raise LedgerConflict(f"Prompt {entry['number']} already exists. Validate again and choose overwrite or a new take.")
                        if decision == 'overwrite':
                            if not owner and filename.casefold() not in legacy_outputs:
                                raise LedgerConflict(f"{filename} is not a named batch output; choose a new take to preserve it.")
                            if owner:
                                filename = owner['filename']
                            else:
                                entry['replace_legacy_asset_id'] = legacy_outputs[filename.casefold()]
                        else:
                            take = 2
                            while f"{entry['number']}_take-{take}.mp4".casefold() in used:
                                take += 1
                            filename = f"{entry['number']}_take-{take}.mp4"
                    used.add(filename.casefold())
                    entry['filename'] = filename
                    entry['admission_key'] = f'batch-{batch_id}-{position}'
                    db.execute('INSERT INTO t2v_batch_output_names VALUES(?,?,?) ON CONFLICT(workspace_id,filename) DO UPDATE SET clip_id=excluded.clip_id',
                               (workspace_id, filename, entry['admission_key']))
                encoded = json.dumps(entries, sort_keys=True, ensure_ascii=False)
                db.execute('INSERT INTO t2v_batches(batch_id,workspace_id,idempotency_key,manifest_hash,entries_json,state) VALUES(?,?,?,?,?,?)',
                           (batch_id, workspace_id, key, digest, encoded, 'running'))
            db.commit()
        return self.get(batch_id)

    def _save(self, batch_id, state, reason=None, entries=None):
        with self.ledger._connect() as db:
            if entries is None:
                db.execute('UPDATE t2v_batches SET state=?,reason=?,updated_at=CURRENT_TIMESTAMP WHERE batch_id=?', (state, reason, batch_id))
            else:
                db.execute('UPDATE t2v_batches SET state=?,reason=?,entries_json=?,updated_at=CURRENT_TIMESTAMP WHERE batch_id=?',
                           (state, reason, json.dumps(entries, ensure_ascii=False), batch_id))

    def _recover_bindings(self, row, entries):
        # Job admission and manifest binding are separate durable writes. Recover
        # an admitted job before pause/stop as well as before advancing.
        changed = False
        for entry in entries:
            if entry['job_id']:
                continue
            try:
                job = self.jobs.get_by_idempotency_key(workspace_id=row['workspace_id'],
                    idempotency_key=entry.get("admission_key", f"batch-{row['batch_id']}-{entry['number']}"))
            except LedgerNotFound:
                break
            entry['job_id'] = job['job_id']
            changed = True
        if changed:
            self._save(row['batch_id'], row['state'], row['reason'], entries)
        return entries

    def control(self, batch_id, action):
        if action not in {'pause', 'resume', 'stop'}:
            raise ValueError('Choose pause, resume or stop.')
        with self._lock():
            row = self._row(batch_id)
            entries = self._recover_bindings(row, json.loads(row['entries_json']))
            if row['state'] not in {'completed', 'stopped'}:
                if row['state'] == 'stopping' and action != 'stop':
                    raise LedgerConflict('The batch is stopping; wait for cancellation to finish.')
                self._save(batch_id, {'pause':'paused','resume':'running','stop':'stopping'}[action],
                           'Paused; the current clip may finish.' if action == 'pause' else None)
                if action == 'stop':
                    self._cancel_entries(entries)
        return self.get(batch_id)

    def _cancel_entries(self, entries):
        # Persist cancellation now, even while the supervisor is blocked waiting
        # for a render. Its existing owned-prompt polling performs the interrupt.
        pending = False
        for entry in entries:
            if not entry['job_id']:
                continue
            with self.ledger._connect() as db:
                take = db.execute('SELECT project_id,take_id,status FROM production_takes WHERE job_id=?', (entry['job_id'],)).fetchone()
            if take and take['status'] in {'refinement_pending','queued','submitting','running','collecting','recovery_required','cancel_requested'}:
                pending = True
                target = 'cancelled' if take['status'] in {'queued', 'refinement_pending'} else 'cancel_requested'
                if take['status'] != target:
                    try:
                        self.ledger.transition_take(project_id=take['project_id'], take_id=take['take_id'], status=target, payload={'reason':'Owner stopped T2V batch.'})
                    except LedgerConflict:
                        pass  # Concurrent completion is reconciled on the next tick.
        return pending

    def advance_active(self, readiness):
        """Called only by the existing worker supervisor, including after restart."""
        queued = False
        with self._lock():
            with self.ledger._connect() as db:
                rows = db.execute("SELECT * FROM t2v_batches WHERE state IN ('running','waiting_for_readiness','waiting_for_recovery','stopping') ORDER BY created_at").fetchall()
            for row in rows:
                entries = self._recover_bindings(row, json.loads(row['entries_json']))
                batch_id = row['batch_id']
                if row['state'] == 'stopping':
                    pending = self._cancel_entries(entries)
                    if not pending:
                        self._save(batch_id, 'stopped', 'Stopped by you. No further prompts will start.')
                    continue
                next_entry = None
                for entry in entries:
                    if not entry['job_id']:
                        next_entry = entry
                        break
                    try:
                        job = self.jobs.get_job(entry['job_id'])
                    except LedgerNotFound:
                        self._save(batch_id, 'paused', f"Prompt {entry['number']}: saved job is missing. No resubmission.")
                        break
                    if row['state'] == 'waiting_for_recovery' and job['status'] != 'recovery_required':
                        # Reconcile the same saved job; never create a replacement.
                        self._save(batch_id, 'running')
                    if self._complete(job):
                        continue
                    if job['status'] == 'refinement_pending':
                        # A validated original is ready for the later LTX phase.
                        # Admit the next H3 serially; the ledger gates refinement
                        # until every entry has reached this checkpoint.
                        continue
                    if job['status'] in {'needs_review','accepted','failed','cancelled','rejected','stale','recovery_required','submission_unknown'}:
                        error = job.get('error') or {}
                        transient = job['status'] == 'recovery_required' and isinstance(error, dict) and error.get('code') == 'comfy_status_unavailable'
                        detail = error.get('message') if isinstance(error, dict) else str(error)
                        state = 'waiting_for_recovery' if transient else 'paused'
                        reason = ("Waiting for ComfyUI to confirm the same saved job; no resubmission."
                                  if transient else "Output must exist and be valid before continuing.")
                        self._save(batch_id, state, f"Prompt {entry['number']}: {job['status']}. {detail or ''} {reason}")
                    break  # One outstanding job only; never submit its successor yet.
                else:
                    if all(self._complete(self.jobs.get_job(e['job_id'])) for e in entries):
                        self._save(batch_id, 'completed')
                if next_entry:
                    ready = readiness()
                    if not ready.get('available'):
                        self._save(batch_id, 'waiting_for_readiness', ready.get('reason') or 'Waiting for T2V readiness.')
                        continue
                    # Stable key recovers a crash between job admission and saving its binding.
                    try:
                        job = self.jobs.create_job(workspace_id=row['workspace_id'],
                            clip_id=next_entry.get("admission_key", f"batch-{batch_id}-{next_entry['number']}"),
                            idempotency_key=next_entry.get("admission_key", f"batch-{batch_id}-{next_entry['number']}"), request=next_entry['request'])
                    except (ValueError, LedgerConflict) as exc:
                        self._save(batch_id, 'paused', str(exc))
                        continue
                    next_entry['job_id'] = job['job_id']
                    self._save(batch_id, 'running', entries=entries)
                    queued = True
        return queued
