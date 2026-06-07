# 12 — Spike 2 / Option 2 Scope: Iterative 3D Bake

**What:** make a *consistent* generative hairstyle on the 3D head model by
iteratively editing rendered views with a 2D diffusion editor and updating the
model until it converges. (Instruct-NeRF2NeRF / Instruct-GS2GS / GaussianEditor
family.) This is the make-or-break build for the product.

## Goal & success criteria
- **Input:** a reconstructed 3D head model (Gaussian Splatting) + its posed views.
- **Output:** the *same* model with a requested hairstyle baked in, **consistent
  from every angle** (no flicker), identity preserved.
- **Pass test:** render a turntable of the baked model → the hair is the **same
  haircut across the whole turn** (vs the per-frame flicker baseline in
  [doc 11](11-spike2-generative-tests.md)), face unmistakably the person.

## The loop
```
reconstructed GS model (+ posed views)
  repeat until converged:
    1. render the model from the training views
    2. edit each render with the 2D editor (Flux Kontext: "add <style>"), masked to
       the HAIR region only (face pixels kept from the render → protects identity)
    3. replace the training targets with the edited views (dataset update)
    4. continue-train the GS model a few hundred iters toward the edited targets
  → the 3D model's single-representation constraint + iteration averages out the
    per-view disagreements → converges to ONE coherent 3D hairstyle
```

## Stack (moves to cloud CUDA)
- **GPU:** single **H100** (or A100/L40S) on RunPod / Lambda. (Iterative edit+retrain
  is far too slow on the M1 Max — see Spike 1's 1.5h 30k run.)
- **GS + editing framework:** **nerfstudio + gsplat**, using the **`igs2gs`
  (Instruct-GS2GS)** method as the base loop. This is the mature CUDA ecosystem
  for exactly this; we move off Brush/Metal (great for local proof, wrong for the
  cloud editing loop).
- **2D editor:** **Flux Kontext** (proven strong + identity-preserving in Spike 2A).
  - First runs: **BFL API** (simple; cost = #edits × $0.04).
  - Optimization: **self-host Flux on the same GPU** (no per-edit cost, faster loop).
  igs2gs ships with InstructPix2Pix — we swap in Flux Kontext for quality.
- **Hair masking:** reuse the `jonathandinu/face-parsing` segmenter (from Spike 1)
  to mask edits to the hair region — keeps the face fixed, stabilizes convergence,
  protects identity. **Important for the add-hair case.**
- **Poses:** pycolmap (already working).

## Key design decisions
- **Mask edits to hair region** (yes) — protect identity + speed convergence.
- **Seed hair-region gaussians** before the loop — the bald model has *no* gaussians
  where new hair goes; pre-seed a rough hair volume (or rely on densification) so the
  optimizer has something to grow. This is the crux of the add-hair (geometry) case.
- **Edit cadence** — re-edit views every N train iters (igs2gs default ~ every few k).
- **Continue from the reconstructed model**, don't train from scratch.

## Minimal first experiment (de-risk cheaply)
- One model (existing IMG_8057, or ideally a fresh **clean** capture so the base
  isn't the limiter), ~30–50 views.
- Run the igs2gs loop with Flux Kontext + hair mask for one style ("medium brown
  wavy hair").
- **Judge:** does the baked turntable show a *consistent* hairstyle (vs per-frame
  flicker)? At acceptable quality? Identity intact?

## Risks (ordered) & mitigations
1. **Convergence for a LARGE add-hair (geometry) edit** — biggest unknown. These
   methods excel at recolor/moderate restyle; *adding* hair volume is hardest.
   Mitigate: pre-seed hair gaussians, allow densification, hair-region masking,
   more iterations. *This is the risk the minimal experiment must retire.*
2. **Identity/face drift** — mitigate with hair-region masking (face pixels frozen).
3. **Casual-capture base quality** — the Spike-1 ceiling; mitigate with a clean capture.
4. **Cost/latency at scale** — self-host the editor; later move to feed-forward.

## Cost & time (rough)
- **Per experiment:** ~2–4 GPU-hours (H100 @ ~$2.5/hr) = **$5–10**, plus editor cost
  (~hundreds of edits × $0.04 ≈ **$10–30** via API, or ~free if self-hosted).
- **Setup effort:** standing up nerfstudio + igs2gs + Flux integration + masking +
  hair-seeding on a cloud box = **a few days of real engineering** (this is R&D, not
  wiring).
- **Minimal first result:** ~a few days + **$20–50** of cloud/API.

## Decisions needed before building
1. **Cloud GPU provider** (RunPod vs Lambda vs Vast) + budget for first experiments.
2. **Capture:** reuse IMG_8057 model, or shoot one **clean** capture first (recommended).
3. **Editor:** Flux via BFL API for speed of setup, or invest in self-hosting up front.
4. **Resourcing:** this is the point where the spike becomes a real R&D project — do
   we proceed solo/iteratively, or bring in more help / more compute.
