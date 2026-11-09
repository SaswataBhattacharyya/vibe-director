# Frame workflow provenance

The three JSON graphs in this change are configuration graphs supplied in the
owner's installed frame-pipeline handoff, copied from
`/home/riki/web_dev/setup_comfy_and-stuff/workflows/ricky/api/`:

- `flux_kontext_recursive_frame.api.json`
- `film_frame_interpolation.api.json`
- `rife_frame_interpolation.api.json`

No third-party node implementation, weights or environment is copied into this
repository. Nodes and models run in the existing ComfyUI installation. The local
installation report and model manifest remain authoritative for exact downloads,
checksums, attribution and model terms:
`env_setup/shared_krita_vibe_20261108/INSTALL_REPORT.md` and `MODEL_MATRIX.csv`
in that external checkout. The handoff is preserved in
`docs/VIBE_DIRECTOR_FRAME_PIPELINE.md` here.

The supplied installation report records Apache-2.0 for upstream FILM, MIT for
upstream RIFE, and separate converted-weight repository terms. It records
noncommercial/nonproduction restrictions on Kontext Dev model use and distinct
output terms. This integration does not grant model-use rights. Retain the
installed upstream notices and review those terms for the intended deployment.

Optional ControlNet and MOSAIC are not enabled by these graphs.
