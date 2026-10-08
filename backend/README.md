# Isolated video CPU review slice

This directory contains the first CPU-only isolated-video review slice for Vibe Director: exact copies of the MiniMax H3 T2V compiler, its shared graph compiler dependency, and its API workflow JSON, plus a new isolated request validator/preview and focused standard-library tests. The proposed API examples elsewhere in this package are contracts for review, not live endpoints. This slice adds no HTTP routes, durable job service, readiness check, or live rendering.

## CPU-only check

From this directory, run:

```sh
PYTHONPATH=. python -m unittest discover -s story_builder/tests -v
```

This reads the copied JSON graph and compiles preview-only graphs in memory. It does not inspect installed models or ComfyUI, persist data, call a provider, queue a job, or render video. Preview duration is predicted from frame count at 24 fps and is not probed output duration.

## Provenance and notices

Source repository: `https://github.com/SaswataBhattacharyya/mooV_E_maker`, commit `2023bf5bce1a808b2624fb5789b4b2a1e8b7b8db`.

| Copied source | Upstream Git blob SHA | Local SHA256 |
|---|---|---|
| `services/minimax_h3_t2v.py` | `78b9642aaf0e04b7934c2fdaace3c72f712f3644` | `c17ba00efb7b873bd256afa978d7b2eee13ac18395d92d48ee1e63151d88d712` |
| `services/minimax_h3_graph_compiler.py` | `fdaa830a1206e3f7feaf34737200e34db45de570` | `a1355882cf07f395a0ce5ba561c290e7e8e64e989d27ac4f59b0404e01cfaef3` |
| `workflows/api/minimax_h3_t2v_api.json` | `476bdadbbe880fef4f32bcfeb25bacfa0b552dec` | `4735e3662333493d488bc2ba6970810e620c13196ccac15b1155010e8cf3e1f9` |

All three files were fetched through the GitHub connector at the pinned commit; connector blob SHAs match local `git hash-object` results. The local reference tree and fetched upstream root both lack a root `LICENSE` and `NOTICE` at this commit; the selected files contain no explicit copyright/license header. The owner authorized reuse of the owner's own source for this bounded slice. No third-party implementation was imported. Preserve/confirm any source notices discovered during canonical integration.
