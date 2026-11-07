"""Project-local editing state, revision approvals and shared Media Prep jobs."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .agent_skills import read_content
from typing import Any

from . import media_library, video_repertoire
from .storage_paths import load_project_documents, save_project_documents

PROFILE = "local-owner"
HUB = Path(__file__).resolve().parents[3] / "design/vibe-editor"
APP_ROOT = HUB.parent
ACTIVE = {"queued", "running", "cancel_requested"}


def now():
    return datetime.now(timezone.utc).isoformat()


def text(value, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"Enter text between 1 and {limit} characters.")
    return value.strip()


def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise ValueError("Invalid project or style ID.")
    return value


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
        temp = stream.name
    os.replace(temp, path)


@contextmanager
def state(root, *, readonly=False):
    folder = Path(root) / "services/editor"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = folder / "state.json"
        data = json.loads(path.read_text()) if path.exists() else {"version": 1, "profile": PROFILE, "projects": [], "styles": []}
        data = load_project_documents(root, data)
        yield data
        if not readonly:
            write(path, save_project_documents(root, data, "editor", write))


def project(data, project_id):
    ident(project_id)
    item = next((p for p in data["projects"] if p["id"] == project_id), None)
    if item is None:
        raise ValueError("Editor project not found.")
    return item


def style(data, style_id):
    item = next((s for s in data["styles"] if s["id"] == style_id), None)
    if item is None:
        raise ValueError("Style not found.")
    return item


def clarification_questions(questions):
    """Approval belongs to the clearance control, not the missing-detail list.

    Match only a standalone approval question about this brief. Mixed questions
    and requests about other decisions must still block approval.
    """
    approval = re.compile(
        r"(?:do you approve|would you approve|can you approve|are you ready to approve) "
        r"(?:(?:the|this) )?(?:revision \d+ )?(?:creative )?brief[?.!]*",
        re.IGNORECASE,
    )
    return [q for q in questions if not approval.fullmatch(q.strip())]


def snapshot(root):
    with state(root) as data:
        result = copy.deepcopy(data)
        for item in result["projects"]:
            pending = item.get("pending", {})
            if pending.get("kind") == "brief":
                value = pending["value"]
                value["questions"] = clarification_questions(value.get("questions", []))
        return result


def add_project(root, body):
    with state(root) as data:
        item = {"id": "edit-" + uuid.uuid4().hex[:16], "name": text(body.get("name"), 100),
                "workspace_id": ident(body.get("workspace_id")), "style_id": None, "revision": 0,
                "created_at": now(), "updated_at": now(), "messages": [], "revisions": [],
                "selection": [], "overrides": {}, "view": {}, "job_id": None}
        data["projects"].append(item)
        return copy.deepcopy(item)


def change_style(root, body, style_id=None):
    with state(root) as data:
        if style_id:
            item = style(data, style_id)
            action = body.get("action")
            if action == "forget":
                item["rules"] = [r for r in item["rules"] if r["id"] != body.get("rule_id")]
            elif action == "reset":
                item["rules"] = []
            elif action in {"propose", "confirm", "edit"}:
                if action == "propose":
                    item["rules"].append({"id": uuid.uuid4().hex, "text": text(body.get("text")), "confirmed": False, "provenance": "owner-chat", "created_at": now()})
                else:
                    rule = next((r for r in item["rules"] if r["id"] == body.get("rule_id")), None)
                    if not rule:
                        raise ValueError("Rule not found.")
                    if action == "edit":
                        rule["text"] = text(body.get("text"))
                    rule["confirmed"] = True
            elif action == "rename":
                name = text(body.get("name"), 80)
                if any(s["id"] != style_id and s["name"].casefold() == name.casefold() for s in data["styles"]):
                    raise ValueError("That style name already exists.")
                item["name"] = name
            else:
                raise ValueError("Unknown style action.")
            item["version"] += 1
        else:
            name = text(body.get("name"), 80)
            if any(s["name"].casefold() == name.casefold() for s in data["styles"]):
                raise ValueError("That style name already exists.")
            item = {"id": "style-" + uuid.uuid4().hex[:16], "name": name, "profile": PROFILE,
                    "version": 1, "rules": [], "created_at": now()}
            data["styles"].append(item)
        return copy.deepcopy(item)


def saved_job(p):
    if not p.get("job_id"):
        return None
    try:
        return video_repertoire.read_job("vibe-editor", p["job_id"])
    except FileNotFoundError:
        return {"status": "missing", "stage": "recovery", "progress": 0, "message": "Saved job is missing. Project inputs and approvals remain available; describe the edit again to prepare a new revision."}


def busy(p):
    job = saved_job(p)
    if job:
        if job["status"] in ACTIVE:
            raise ValueError("A job is active. Stop it or wait before changing this revision.")


def validate_selection(root, workspace, values):
    if not isinstance(values, list) or len(values) > 100:
        raise ValueError("Choose at most 100 media ranges.")
    result = []
    for row in values:
        if not isinstance(row, dict):
            raise ValueError("Each media range must be an object.")
        asset_id = text(row.get("asset_id"), 80)
        source, mime, filename = media_library.asset_path(root, workspace, asset_id)
        start, end = float(row.get("start", 0)), float(row.get("end", 5))
        if not all(math.isfinite(n) for n in (start, end)) or not 0 <= start < end <= 86400:
            raise ValueError("Each range needs valid in/out seconds.")
        kind = mime.split("/")[0]
        probe = media_library._probe(source, kind)
        if kind in {"video", "audio"} and end > probe["duration_seconds"] + .05:
            raise ValueError(f"Range exceeds the duration of {filename}.")
        info = source.stat()
        result.append({"asset_id": asset_id, "start": start, "end": end, "filename": filename,
                       "mime": mime, "size": info.st_size, "mtime_ns": info.st_mtime_ns})
    return result


def update_project(root, project_id, body):
    with state(root) as data:
        p = project(data, project_id)
        if body.get("view") is not None:
            p["view"].update({k: v for k, v in body["view"].items() if k in {"tab", "position", "selected_asset", "export_folder", "export_filename"}})
        changes = set(body) - {"view"}
        if changes:
            busy(p)
            if "style_id" in body:
                if body["style_id"]:
                    style(data, body["style_id"])
                p["style_id"] = body["style_id"] or None
                p.pop("brief", None)
            if "selection" in body:
                p["selection"] = validate_selection(root, p["workspace_id"], body["selection"])
            if "override" in body:
                key = p.get("style_id") or "default"
                p["overrides"][key] = str(body["override"])[:4000]
                p.pop("brief", None)
            p["revision"] += 1
            if changes == {"selection"} and p.get("pending", {}).get("kind") == "brief":
                p["pending"]["revision"] = p["revision"]
            else:
                p.pop("pending", None)
        p["updated_at"] = now()
        return copy.deepcopy(p)


def message(p, role, content):
    p["messages"].append({"id": uuid.uuid4().hex, "role": role, "content": content, "at": now(), "style_id": p.get("style_id")})


def _enqueue(p, operation, **extra):
    request = {"operation": operation, "project_id": p["id"], "workspace_id": p["workspace_id"],
               "revision": p["revision"], **extra}
    job = video_repertoire.create_job("vibe-editor", request)
    p["job_id"] = job["job_id"]
    return job


def command(root, project_id, body, *, agent_request=None, on_created=None):
    start = None
    with state(root) as data:
        p = project(data, project_id)
        action = body.get("action", "chat")
        if agent_request is not None:
            from . import agent_editor
            if action != 'prepare_brief':
                raise ValueError('The agent bridge can only prepare an Editor brief.')
            settings = agent_request['agent_settings']
            agent_editor.check_target(p, agent_request['workspace_id'], settings['target'])
            if agent_editor.style_snapshot(data, p) != settings['style_snapshot']:
                raise ValueError('Editor style changed. Prepare a new proposal.')
        if action == "stop":
            if p.get("job_id"):
                video_repertoire.cancel_job("vibe-editor", p["job_id"])
            message(p, "assistant", "Stopped the editor job. Your project and approved revisions remain saved.")
        elif action == "pause":
            p["pause_requested"] = True
            message(p, "assistant", "Pause requested. The current render can finish; export will wait for Resume.")
        elif action == "resume":
            p["pause_requested"] = False
        elif action == "retry":
            busy(p)
            previous = video_repertoire.read_job("vibe-editor", p["job_id"]) if p.get("job_id") else None
            if not previous or previous["status"] not in {"failed", "error", "cancelled", "interrupted"}:
                raise ValueError("Only a failed or stopped editor job can be retried.")
            request = previous["request"]
            if request["revision"] != p["revision"]:
                raise ValueError("This job belongs to an older revision. Describe the edit again.")
            start = _enqueue(p, request["operation"], **{k: v for k, v in request.items() if k not in {"operation", "revision", "workspace_id", "project_id"}})
            p["pause_requested"] = False
            message(p, "assistant", "Retrying the same saved revision and approved inputs.")
        else:
            busy(p)
            if body.get("revision") != p["revision"]:
                raise ValueError("This view is stale. Refresh and review the current revision.")
            if action == "restore_plan":
                saved = next((r for r in p['revisions'] if r['revision'] == body.get('saved_revision') and r['kind'] == 'plan'), None)
                if not saved:
                    raise ValueError('Saved approved timeline not found.')
                value = validate_plan(root, p['workspace_id'], saved['value'])
                p['selection'] = value['clips'] + ([value['audio']] if value['audio'] else [])
                p['revision'] += 1
                p['pending'] = {**copy.deepcopy(saved), 'revision': p['revision'], 'value': value}
                message(p, 'assistant', 'Saved timeline restored as a proposal. Review media and tools again before rendering.')
                return copy.deepcopy(p)
            if action == "prepare_plan":
                if not p.get("brief") or not p["selection"]:
                    raise ValueError("Approve the brief and select media ranges first.")
                start = _enqueue(p, "plan", brief=p["brief"], selection=p["selection"], style_snapshot=p.get("brief_style_snapshot", {"id": None, "version": 0, "rules": []}))
                message(p, "assistant", "Preparing selected media and tool plan for clearance 2.")
            content = text(body.get("text") or ("Approve" if action == "approve" else "Prepare media plan" if action == "prepare_plan" else ""), 12000)
            pending = p.get("pending")
            # Only a standalone explicit assent resolves the currently visible clearance.
            assent = content.casefold().strip(".! ") in {"yes", "approve", "yes apply", "yes, apply", "apply", "go ahead", "approved"}
            if action == "prepare_plan":
                pass
            elif action == "approve" or (action == 'chat' and pending and assent):
                if not pending or pending["revision"] != p["revision"]:
                    raise ValueError("There is no current clearance to approve.")
                message(p, "user", content)
                p["revisions"].append(copy.deepcopy(pending))
                p.pop("pending")
                if pending["kind"] == "brief":
                    pending["value"]["questions"] = clarification_questions(pending["value"].get("questions", []))
                    if pending["value"]["questions"]:
                        raise ValueError("Answer the clarification questions in chat before approving the brief.")
                    p["brief"] = pending["value"]
                    p["brief_style_snapshot"] = pending["style_snapshot"]
                    if p["selection"]:
                        start = _enqueue(p, "plan", brief=p["brief"], selection=p["selection"], style_snapshot=pending["style_snapshot"])
                        message(p, "assistant", "Creative brief approved. Preparing the selected media and tool plan for clearance 2.")
                    else:
                        message(p, "assistant", "Creative brief approved. Find media in the Media panel, select exact ranges, then choose Prepare media and tool plan.")
                else:
                    if not pending["value"].get("clips"):
                        raise ValueError("Select media before rendering.")
                    start = _enqueue(p, "render", plan=pending["value"], style_snapshot=pending["style_snapshot"],
                                     **({'review_evidence': pending['evidence']} if pending.get('evidence') else {}))
                    p["pause_requested"] = False
                    message(p, "assistant", "Media and tool plan approved. Rendering this exact revision.")
            else:
                if action not in {"chat", "prepare_brief"}:
                    raise ValueError("Unknown editor action.")
                p["revision"] += 1
                p.pop("pending", None)
                p.pop("brief", None)
                selected_style = copy.deepcopy(style(data, p["style_id"])) if p.get("style_id") else {"id": None, "version": 0, "rules": []}
                selected_style["rules"] = [r for r in selected_style["rules"] if r["confirmed"]]
                selected_style["project_override"] = p["overrides"].get(p.get("style_id") or "default", "")
                message(p, "user", content)
                start = _enqueue(p, "brief", prompt=content, selection=p["selection"], style_snapshot=selected_style,
                                 **({k: v for k, v in agent_request.items() if k != 'workspace_id'} if agent_request else {}))
        p["updated_at"] = now()
        result = copy.deepcopy(p)
    if start:
        if on_created:
            on_created(start)
        video_repertoire.start_job("vibe-editor", start["job_id"])
    return result


def validate_plan(root, workspace, value):
    if not isinstance(value, dict) or not isinstance(value.get("clips"), list) or not 1 <= len(value["clips"]) <= 100:
        raise ValueError("The plan needs 1–100 selected video/image clips.")
    width, height, fps = int(value.get("width", 1280)), int(value.get("height", 720)), int(value.get("fps", 24))
    if not (128 <= width <= 3840 and 128 <= height <= 3840 and width % 2 == 0 and height % 2 == 0 and fps in {24, 25, 30, 60}):
        raise ValueError("Unsupported composition dimensions or frame rate.")
    clips = validate_selection(root, workspace, value["clips"])
    if any(not c["mime"].startswith(("video/", "image/")) for c in clips):
        raise ValueError("Timeline clips must be images or videos. Use the audio track for sound.")
    from . import editor_effects
    for index, (c, original) in enumerate(zip(clips, value["clips"])):
        c["caption"] = str(original.get("caption", ""))[:500]
        c["fit"] = original.get("fit", "contain")
        if c["fit"] not in {"contain", "cover"}:
            raise ValueError("Choose contain or cover fit.")
        editor_effects.validate(c, original, last=index == len(clips)-1)
    for i, c in enumerate(clips[:-1]):
        if c["transition"]["duration"] > min(c["render_duration"], clips[i+1]["render_duration"])/2:
            raise ValueError("A transition must fit within half of each neighboring clip.")
    if sum(c["render_duration"] for c in clips) > 600:
        raise ValueError("Keep each editor composition within ten minutes.")
    audio = validate_selection(root, workspace, [value["audio"]]) if value.get("audio") else []
    if audio and not audio[0]["mime"].startswith("audio/"):
        raise ValueError("Choose an audio asset for the soundtrack.")
    return {"summary": str(value.get("summary", "Sequential cuts with optional captions and audio."))[:4000],
            "tools": ["HyperFrames", "FFmpeg"], "width": width, "height": height, "fps": fps,
            "clips": clips, "audio": audio[0] if audio else None}


def selected_plan(root, p, raw):
    value = validate_plan(root, p['workspace_id'], raw)
    for clip in value['clips'] + ([value['audio']] if value['audio'] else []):
        if not any(r['asset_id'] == clip['asset_id'] and r['start'] <= clip['start'] and clip['end'] <= r['end'] for r in p['selection']):
            raise ValueError('The timeline exceeds the selected media ranges. Select and review those ranges first.')
    return value


def propose_plan(root, project_id, body, *, evidence=None):
    with state(root) as data:
        p = project(data, project_id)
        busy(p)
        if body.get("revision") != p["revision"]:
            raise ValueError("Stale revision. Refresh before saving a plan.")
        if not p.get("brief"):
            raise ValueError("Approve the creative brief first.")
        value = selected_plan(root, p, body.get("plan"))
        p["revision"] += 1
        selected = style(data, p["style_id"]) if p.get("style_id") else {"id": None, "version": 0, "rules": []}
        selected = copy.deepcopy(selected)
        selected["rules"] = [r for r in selected["rules"] if r["confirmed"]]
        selected["project_override"] = p["overrides"].get(p.get("style_id") or "default", "")
        p["pending"] = {"kind": "plan", "revision": p["revision"], "value": value, "style_snapshot": copy.deepcopy(selected)}
        if evidence is not None:
            p['pending']['evidence'] = copy.deepcopy(evidence)
        message(p, "assistant", "Review the updated media and tool plan below. Approval is required before rendering.")
        return copy.deepcopy(p)


def _conversation(root, request):
    with state(root) as data:
        p = project(data, request["project_id"])
        return [m for m in p["messages"] if m.get("style_id") == request["style_snapshot"].get("id")][-12:]


def run_job(root, job_id, request, progress):
    operation = request["operation"]
    if operation == "render":
        from .vibe_editor_render import render
        result = render(root, job_id, request, progress)
        with state(root) as data:
            p = project(data, request["project_id"])
            # render() publishes under the project lock; a later Stop cannot undo that completed publication.
            p["output"] = result
            message(p, "assistant", "Render completed and validated. Review the video in Preview; export when ready.")
        return result
    from . import reasoning_provider
    progress("reasoning", "Preparing " + operation + " with the selected Director model.", 10)
    guides = read_content(HUB / "skills", "vibe-editor-director/SKILL.md")
    common = (guides + "\nReturn JSON only. Current explicit request > this style's project override > its confirmed rules. "
        "Other style/user preferences must never be retrieved. Do not run tools or create files. "
        "Explain editing terminology in ordinary language. Never invent file paths or asset IDs.\n"
        + json.dumps(request, ensure_ascii=False)
        + "\nPrior chat in THIS project/style only: " + json.dumps(_conversation(root, request), ensure_ascii=False))
    if operation == "brief":
        schema = {"type": "object", "properties": {"summary": {"type": "string"}, "questions": {"type": "array", "items": {"type": "string"}}, "preference_proposal": {"type": "string"}}, "required": ["summary", "questions", "preference_proposal"], "additionalProperties": False}
        prompt = common + '\nInterpret the requested edit into a concrete creative brief (scope, pace, audio, format, preserve). Ask up to three essential clarification questions only if necessary. Never put approval/confirmation requests in questions: the UI provides a separate approval button. If no creative details are missing, return questions: []. Return {"summary":"...", "questions":[], "preference_proposal":"one durable interpretation explicitly supported by the owner, or empty string"}. Never propose a rule already confirmed. Approval of the brief does NOT confirm this learning.'
    else:
        schema = None
        prompt = common + '\nPropose a concrete executable plan from ONLY the selected assets/ranges. Supported now: sequential cuts and overlapping transitions, image holds, contain/cover framing, static captions, source audio or one replacement audio track, final width/height/fps. Per clip effect={preset:none|cinematic|vhs|black-white,strength:0..1}. speed={start:0.25..4,end:0.25..4} is a continuous speed ramp across the video source range (1,1 is normal). Audio follows the ramp with finely sliced tempo changes. transition={kind:cut|dissolve|domain-warp|whip-pan|cinematic-zoom|glitch|light-leak|cross-warp-morph,duration:0.1..3} leads into the next clip, overlaps both, and must fit in half of both clips. Last transition must be cut. cross-warp-morph is a warp/blend transition, not AI subject transformation. Preserve default none/1x/cut unless requested. Return {"summary":"...", "tools":["HyperFrames","FFmpeg"], "width":1280,"height":720,"fps":24,"clips":[{"asset_id":"selected ID","start":0,"end":5,"caption":"","fit":"contain"}],"audio":null}. If a specialist (Blender/FreeCAD/generation) or unsupported operation is needed, return {"blocker":"Explain the missing adapter and required step"}; never silently substitute tools.'
    value = reasoning_provider.generate_json(prompt=prompt, include_director_lessons=False, output_schema=schema)
    if operation == "brief":
        value = {"summary": text(value.get("summary"), 8000), "questions": clarification_questions([text(q, 1000) for q in value.get("questions", [])[:3]]), "preference_proposal": str(value.get("preference_proposal", ""))[:2000].strip()}
    elif value.get("blocker"):
        with state(root) as data:
            p = project(data, request["project_id"])
            if p["revision"] != request["revision"] or video_repertoire.read_job("vibe-editor", job_id)["status"] in {"cancelled", "cancel_requested"}:
                raise ValueError("Revision changed or job stopped; result was not applied.")
            message(p, "assistant", "Cannot execute this plan yet: " + str(value["blocker"])[:4000])
        return {"blocked": True, "reason": value["blocker"]}
    else:
        selected_ids = {r["asset_id"] for r in request.get("selection", [])}
        if any(r.get("asset_id") not in selected_ids for r in value.get("clips", [])):
            raise ValueError("The plan used unselected media. Choose those assets before approval.")
        if value.get("audio") and value["audio"].get("asset_id") not in selected_ids:
            raise ValueError("The plan used an unselected soundtrack.")
        value = validate_plan(root, request["workspace_id"], value)
        for clip in value["clips"] + ([value["audio"]] if value["audio"] else []):
            if not any(r["asset_id"] == clip["asset_id"] and r["start"] <= clip["start"] and clip["end"] <= r["end"] for r in request["selection"]):
                raise ValueError("The plan exceeds a selected media range. Select the wider range before planning.")
    with state(root) as data:
        p = project(data, request["project_id"])
        current = video_repertoire.read_job("vibe-editor", job_id)
        if p["revision"] != request["revision"] or current["status"] in {"cancelled", "cancel_requested"}:
            raise ValueError("Revision changed or job was stopped; result was not applied.")
        p["pending"] = {"kind": operation, "revision": p["revision"], "value": value, "style_snapshot": request["style_snapshot"]}
        if operation == "brief" and p.get("style_id") and value.get("preference_proposal"):
            memory = style(data, p["style_id"])
            proposal = value["preference_proposal"]
            if not any(r["text"].casefold() == proposal.casefold() for r in memory["rules"]):
                memory["rules"].append({"id": uuid.uuid4().hex, "text": proposal, "confirmed": False, "provenance": f"editor-project:{p['id']}:revision:{p['revision']}", "created_at": now()})
                memory["version"] += 1
                message(p, "assistant", "Proposed style learning (not applied): " + proposal + "\nReview and confirm it separately in the Style panel.")
        message(p, "assistant", value.get("summary", "Review this plan.") + "\n" + "\n".join(value.get("questions", [])))
    return {"pending_clearance": operation, "revision": request["revision"]}


def export_video(root, project_id, body):
    import shutil
    with state(root) as data:
        p = project(data, project_id)
        output = p.get("output")
        if not output:
            raise ValueError("Render and validate a final video before exporting.")
        source, _, _ = media_library.asset_path(root, p["workspace_id"], output["asset"]["asset_id"])
        folder = Path(text(body.get("folder"), 2000)).expanduser()
        if not folder.is_absolute() or not folder.is_dir():
            raise ValueError("Choose an existing absolute output folder.")
        filename = text(body.get("filename"), 150)
        if Path(filename).name != filename or not filename.lower().endswith(".mp4"):
            raise ValueError("Use a plain .mp4 filename without directories.")
        target = folder.resolve() / filename
        if target.is_symlink() or target.resolve() == source.resolve():
            raise ValueError("Choose a different export destination.")
        if p.get("pause_requested"):
            raise ValueError("Resume the editor before exporting.")
        def digest_file(path):
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        exists = target.exists()
        expected = body.get("existing_sha256")
        if exists:
            digest = digest_file(target)
            if not body.get("overwrite") or expected != digest:
                return {"collision": True, "path": str(target), "existing_sha256": digest}
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as stream:
            staged = Path(stream.name)
            try:
                with source.open("rb") as original:
                    shutil.copyfileobj(original, stream)
                stream.flush()
                os.fsync(stream.fileno())
                if exists:
                    if target.is_symlink() or digest_file(target) != expected:
                        raise ValueError("Destination changed. Review overwrite again.")
                    os.replace(staged, target)
                else:
                    # Atomic no-clobber publication. A collision requires a fresh owner choice.
                    os.link(staged, target)
            finally:
                staged.unlink(missing_ok=True)
        p["last_export"] = {"path": str(target), "at": now(), "revision": output.get("asset", {}).get("metadata", {}).get("editor_revision")}
        return {"path": str(target)}
