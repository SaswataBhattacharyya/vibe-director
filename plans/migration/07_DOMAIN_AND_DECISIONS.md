# Domain glossary and migration decisions

## Shared terms

| Term | Meaning / owner | Must remain true |
|---|---|---|
| Project | Saved source, artifacts and asset links; project store | Stable ID; project boundaries checked before reads/writes |
| Production run | One saved authority/route/style/provider configuration and stage history | Changing tabs never creates or changes a run |
| Authority mode | Manual, Semi or Full decision policy | Full does not silently fall back to Manual |
| Making route | Direct, reference-built or hybrid conditioning policy | Required masters follow the route, not a universal UI requirement |
| Production type | Film/ad/news/informative/social/corporate intent | Distinct from voice delivery style and visual recipe |
| Narrative style | Versioned text/style instructions and source citations | Published versions immutable; source provenance retained |
| Director profile | Versioned behavior policy | Independent of narrative wording variants |
| Canon revision | Accepted story/character/world/stage facts | Downstream decisions record their source revision |
| Scene | Narrative unit and continuity boundary | New scene does not inherit stale previous-scene references |
| Shot | Planned ordered unit with duration, dialogue and workflow intent | Shot plan does not imply a rendered output |
| Recipe/workflow | Known media contract, graph/compiler/version and dependencies | UI graph, API graph and style preset distinguished |
| Asset | Owned or shared registered media bytes with role/provenance/hash | Client path not authority; shared links do not transfer ownership |
| Master | Accepted asset assigned to a canon role/identity | A matching filename is insufficient identity binding |
| Voice binding | Stable speaker ID linked to reference asset/transcript | Voice selection/cloning distinct from training |
| Reference plan | Ordered image/video/audio asset roles resolved for a shot | Tags correspond to resolved order; stale validation invalidated |
| Take | Attempted/generated version of one shot | Keep attempts, parent links and exact request/output hashes |
| Accepted take | Exact take approved under stored authority/review policy | Completion alone does not accept a take |
| Sidecar audio | Separate optional dialogue/effect output | Does not silently replace native H3 audio |
| Job | Owner-specific durable or subprocess execution record | Keep prompt IDs/idempotency/recovery; do not flatten state semantics |
| Evidence | Hash/revision-bound observation or review record | Confidence is not identity/truth; uncertainty remains visible |
| Repertoire | Shared reusable sources, clips, analysis and indexes | Project deletion does not delete shared sources |
| Delivery manifest | Explicit selected outputs or legacy raw index | Raw output scan not presented as accepted-only export |
| Fine-tuning | Training model parameters from a dataset | Reference-based inference is not fine-tuning |

## Decision register

| Decision | State | Reason / consequence |
|---|---|---|
| Migrate the existing working website | **Accepted user direction** | Avoid losing functioning work and repeating paid generation/development |
| One working folder named Vibe Director | **Accepted user direction** | Earlier empty duplicate was consolidated; this folder is authoritative |
| Keep installed ComfyUI/models external | Proposed technical choice | Preserves heavy working runtime; configuration remains machine-specific |
| Retain `story_builder` package and relative layout first | Proposed technical choice | Saves import/path churn and makes byte-parity copying reviewable |
| One modular FastAPI app with current queues/stores | Proposed technical choice | Reuses existing recovery logic; incremental routers are sufficient |
| URL-scoped project/run/shot navigation | Proposed UI choice | Prevents stale browser context from mutating another project/run |
| One workspace with orthogonal modes/routes | Proposed product choice | Makes the directing choices composable and comprehensible |
| Preserve optional graphs with honest readiness | Proposed product choice | Retains the arsenal without claiming every recipe is integrated |
| Preserve native output and separate derivatives | Existing behavior to preserve | Audio review and media provenance depend on exact bytes |
| Private owner repo with Ashu as collaborator | User preference/setup pending | Owner retains administration; both participate in issues/PRs/reviews/merges |

No new architectural decision is represented as already implemented. Move accepted technical decisions into concise project ADRs when the implementation trade-off is actually chosen; easily reversible tab/component arrangements do not need formal ADRs.
