# Graphify guide for Vibe Director

Graphify is installed in the `react` Conda environment. The local graph lives at `graphify-out/graph.json` and is a code-only AST index (no external model/API calls). It currently covers the backend, frontend, tools and code tests. Generated graph artifacts are local analysis output, not product requirements.

## Use it during implementation

1. Read the current product contract and phase state first: `plans/README.md`, `plans/remaining_app.md`, `plans/progress_review.md`, plus the relevant stage plan and `plans/HANDOFF.md`.
2. Query the graph for a feature's UI entry points, service/API dependencies, callers and likely affected code. Follow paths across frontend and backend where possible.
3. Open the returned source locations and verify the actual behavior, persisted data, error/recovery paths and current plan constraints. The graph is a navigation aid; it does not establish feature completion or acceptance.
4. After a substantial code change, refresh the graph and use `affected`/`query` to orient the next slice.
5. For UI changes, use Playwright MCP against the intended Vibe app and verify the visible result and interaction. Mock provider/job APIs for software checks; never trigger media generation as part of a browser check.

## Commands

```bash
conda run -n react graphify query "How does [feature] flow from UI to persistence?" --graph graphify-out/graph.json
conda run -n react graphify path "FrontendSymbol" "BackendSymbol" --graph graphify-out/graph.json
conda run -n react graphify affected "ChangedSymbol" --graph graphify-out/graph.json
conda run -n react graphify extract . --code-only --no-cluster
```

The code-only graph intentionally skips Markdown plans. Never use it instead of the authoritative requirements, progress review, or handoff. Ignore historical/dormant modules unless a reachable route or live caller proves they remain relevant.
