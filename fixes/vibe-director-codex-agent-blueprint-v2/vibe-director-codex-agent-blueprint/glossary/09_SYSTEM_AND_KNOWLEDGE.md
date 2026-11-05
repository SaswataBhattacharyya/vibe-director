# System tool guide

Source-backed usage map, 2026-11-05. IDs below are glossary IDs for future routing, not currently registered model functions. Consult [API helpers](API_HELPERS.md) and [HTTP routes](HTTP_ROUTES.md) for exact source locations. Live readiness has not been exercised by this documentation task.

## system.status — Readiness, provider, jobs and GPU safety

**Choose when:** Explain why a task cannot run or monitor real work.

**UI:** #/status

**Inputs:** Workflow/job ID, provider configuration context or status request.

**Outputs:** Capability reasons, queue/admission/worker/provider status and diagnostic evidence.

**How to use:** Use status-api.ts and workflow-specific capabilities; preserve shared dispatch/thermal/provider guards. GPU 90°C cutoff and 2100 MHz ceiling are existing policy, not suggestions to change clocks. Clearing holds/changing workload policy requires an appropriate explicit user action.

**Source:** [status-api.ts](../frontend/src/lib/status-api.ts), [StatusPage.tsx](../frontend/src/StatusPage.tsx), [gpu_runtime.py](../backend/story_builder/services/gpu_runtime.py), [job_queue_status.py](../backend/story_builder/services/job_queue_status.py), [reasoning_status.py](../backend/story_builder/services/reasoning_status.py)

## system.knowledge — Prompt workflow knowledge and installed Director skills

**Choose when:** Select model-specific prompting rules or inspect current Director knowledge.

**UI:** Prompting/Director settings and skill files

**Inputs:** Workflow/model IDs, installed skill paths, approved scoped lessons.

**Outputs:** Versioned guidance/reference and prompt-knowledge provenance.

**How to use:** getWorkflowGuidance plus director_skills.py. Read relevant skills only. Tool descriptions are knowledge; executable adapters are separate. Do not silently rewrite skill approval rules through this glossary.

**Source:** [director_skills.py](../backend/story_builder/services/director_skills.py), [workflow_knowledge.py](../backend/story_builder/services/workflow_knowledge.py), [SKILL.md](../skills/vibe-director/SKILL.md), [SKILL.md](../skills/video-prompting/SKILL.md)
