# hair-spike

Spike for a voice-driven, generative AI hairstyle try-on app: speak a style →
record a short rotate selfie → see a generative hairstyle from every angle.

**Start with [`docs/README.md`](docs/README.md)** — it indexes the full design,
findings, economics, and runbooks. Cloud setup: [`docs/13-runpod-runbook.md`](docs/13-runpod-runbook.md).

## Pipeline scripts
| Script | Does |
|---|---|
| `recon_prep.py` | capture-quality pre-flight (sharpness + curate frames) |
| `recon_sfm.py` | camera poses via pycolmap |
| `recon_run.sh` | full reconstruction: video → frames → SfM → Brush GS → .ply |
| `make_turntable.sh` | render a turntable mp4 from a .ply (via brush-orbit) |
| `hairedit.py` | single-image generative hair edit (BFL/Replicate) |
| `hairswap.py` | per-frame generative hair edit across a video (pluggable backends) |
| `bake.py` | single-round 3D bake (edit views → train GS → render) |
| `remask_bake.py` | bake with hair-region masking (reuses existing edits) |
| `model.py` | unit-economics model |
| `brush-orbit/` | custom headless Gaussian-splat orbit renderer (Rust; drops into the Brush workspace) |

## Not in the repo (regenerated / cloned)
`brush/` (clone from github.com/ArthurBrussee/brush + add `brush-orbit/`), `.venv/`,
`recon/`, `outputs/`, input captures (`in/`). See the runbook.

## Secrets
No keys are committed. The generative backends read `BFL_API_KEY` /
`REPLICATE_API_TOKEN` from the environment.
