# Codex-style agent runtime protocol for user-facing chat

1. On user "make full film": show `Plan` with task DAG, refs, generation/editing stages, QA, cost/resource ceilings, and expected final film. Wait for owner confirmation.
2. On "implement": lock approved plan version; perform tool calls or computer operations within scope and permission profile. Record task status and honest progress. Don't hide incomplete stages behind a final chat response.
3. On failure: reconcile existing jobs/outputs; inspect diagnostics; propose repair or use reversible authorized workaround. New expensive/destructive/external plans require plan update approval.
4. On interruption: persist task/graph state; user may resume, manual takeover or skip individual steps. Never mark incomplete film as done.
5. On request for new tool: first inspect registry; if missing, propose coding integration and ask for approval. Once approved, create adapter in safe code branch, test, register, and use under stated scope.
6. On delegated editing: pass versioned handoff with asset IDs/selected ranges, not a prose-only "please edit". Editor can call same tools and reports actual verified edit/export.
7. On completion: show final playable file and work summary, chosen takes, test/quality report, unresolved caveats and project save state.
