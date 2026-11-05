---
name: project-knowledge-curator
description: Maintain a versioned, source-linked project filmmaking knowledge graph across story, people, scenes, assets, tasks, generations, quality findings, edits and exports.
---
# Project Knowledge Curator
Before acting, fetch current canonical facts and relevant linked assets, hashes, approved settings, previous clip end state, decisions and task status. Use existing DB/media ledger as authority, graph as indexed projection. Distinguish user-approved facts from model inference; keep confidence/provenance. Write graph edges from every operation to existing IDs; no guessed asset paths. Persist conversation/task knowledge per project, and ensure safe project switch isolation and recovery. Avoid loading every raw log into model; retrieve relevant neighborhoods and versioned summaries. Never rewrite old render requests when story/style changes. See `../../05_PROJECT_KNOWLEDGE_GRAPH.md`.
