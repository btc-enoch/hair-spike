# 10 — Spike 1 Results: Local 3D Reconstruction (2026-06-06)

**Goal:** can a casual phone capture reconstruct into a usable 3D head model,
locally on the Mac? **Answer: yes — with the capture as the quality ceiling.**

## The local pipeline we built (all on M1 Max, no cloud)

```
video → ffmpeg frames → pycolmap SfM (poses) → Brush Gaussian Splatting (Metal GPU)
      → .ply → brush-orbit renderer (+ floater cull) → turntable mp4
```

Two Mac blockers, both solved:
- **CUDA not available** → used **Brush** (Rust/wgpu Gaussian-Splatting trainer that
  runs on **Apple Metal**). Built `brush` + a custom headless `brush-orbit` renderer.
- **Homebrew COLMAP feature-matcher SIGBUS-crashes on Apple Silicon** (both CPU and
  GPU matchers) → drove SfM through the **pycolmap** pip wheel instead (`recon_sfm.py`).

## Tooling installed
- Rust toolchain (rustup, cargo 1.96) — self-contained in `~/.cargo`, removable.
- Brush (cloned to `brush/`, built `brush` + added/built `brush-orbit`).
- COLMAP (brew — matcher unusable; kept for nothing) + **pycolmap** (the one used).
- ffmpeg; existing `.venv` (torch/diffusers) reused for pycolmap + frame tools.

## Captures tested
| Clip | Verdict |
|---|---|
| IMG_8052 (reclined) | poor coverage, couch occlusion → rejected |
| IMG_8053 | good coverage BUT soft + lighting jumped (daylight→dim→purple LED) |
| **IMG_8057** | **best**: ear-to-ear coverage incl. crown, daylight, but soft focus |

On IMG_8057: **72/80 frames registered**, 7,226 SfM points.

## Reconstruction results
- **Recognizable, spinnable head**, correct orientation. Frontal/¾ good; sides hazier.
- Main artifact = **floater "fog"** (stray gaussians). Fixed substantially by:
  1. constraining the orbit to the **captured front arc** (full 360 visits unfilmed angles → mush),
  2. a **floater cull** (drop low-opacity / oversized / far gaussians at render time),
  3. **tighter framing** on the subject (IQR-based center/radius).
- 7k model = 331k gaussians; 30k model = **1.18M** gaussians.

## ⚠️ Key finding: 30k iterations did NOT help
- 30k took **~1h35m** and produced a **grainier/noisier** result than 7k+cull.
- It **over-densified** (1.18M gaussians) and **overfit the soft capture** — fitting
  the blur as noise, which shows up as grain from novel angles.
- **7k + cull ≈ or better**, in a fraction of the time.

## Lessons (these save future time/money)
1. **Iterations are not the quality lever.** Sweet spot ≈ **7–15k iters + floater cull**.
2. **The capture is the ceiling** — sharp focus + even constant light matter far more
   than compute. No training fixes a soft capture.
3. **Laptop per-scene optimization is impractically slow** (~1.5h for 30k) → this is
   exactly why production wants **clean capture + cloud GPU / feed-forward**, not max-iters.
4. Production speed target (unchanged): build ~10–30s (feed-forward, cloud), hair-gen
   ~2–8s/style. The 30–95 min we saw is a laptop + max-quality-method artifact.

## Artifacts & scripts (all preserved, non-overwriting)
- `recon_prep.py` — capture-quality pre-flight (sharpness + coverage curation).
- `recon_sfm.py` — pycolmap SfM → COLMAP sparse model.
- `recon_run.sh` — full pipeline; per-run `recon/runs/<label>/`, copies model to `outputs/models/`.
- `make_turntable.sh` — render + encode a **uniquely timestamped** mp4 to `outputs/videos/`.
- `brush/apps/brush-orbit` — headless orbit renderer (Metal) with floater cull.
- Outputs: `outputs/{models,videos,frames}/` — timestamped, never overwritten.
- Saved: 7k + 30k models + their turntables under `outputs/`.

## Status & next
- **Spike 1: complete.** Local reconstruction works; quality is capture-bound; render
  service ("model → video") proven.
- **Spike 2 (next, the make-or-break):** generative hair baked into the model.
  - Not a quick local win — generative quality needs cloud (same lesson as training).
  - **Cheapest first test:** a single **canonical-frame generative hair edit** (cloud
    Flux/Qwen) to confirm identity-preserving edit quality *before* the hard 3D-bake.
