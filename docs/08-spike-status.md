# 08 — Spike Status: What's Built & What's Proven

Workspace: `/Users/woz/hair-spike/` (separate from the user's `btc/enoch` repo).
Hardware: **M1 Max, 64GB**. As of 2026-06-05.

## What's built

```
hair-spike/
  hairswap.py          pluggable-backend pipeline (frame split → edit → reassemble)
  model.py             unit-economics model
  Dockerfile,          containerised orchestration (cloud/API backends only —
  docker-compose.yml     macOS Docker has NO GPU passthrough, so local model
                         runs NATIVELY in the venv, not in Docker)
  .venv/               torch 2.8 + MPS, diffusers, transformers, peft
  in/ frames/ out/ docs/
```

### `hairswap.py` backends
- `local` — SD1.5-inpaint + LCM-LoRA, hair masked via `jonathandinu/face-parsing`,
  runs on MPS. Two mask modes: `hair` (restyle existing) and `grow` (geometry-based
  scalp/halo mask to add hair onto a bald/short head).
- `replicate` — instruction editor (default Flux Kontext) via Replicate API.
- `bfl` — Black Forest Labs native API (submit + poll) for Flux Kontext.

Run: `cd ~/hair-spike && .venv/bin/python hairswap.py --backend local \
  --mask grow --video in/clip.mp4 --style "..." --frames 12`

## What's proven ✅

- **End-to-end pipeline works**: ffmpeg frame split → hair segmentation → masked
  generative inpaint on the GPU → reassembly to `out/edited.mp4` + side-by-side
  `out/compare.mp4`.
- **Identity preservation is excellent** across a real head turn (face/skin/beard/
  background untouched).
- **Speed**: SD1.5+LCM ~3.3s/frame on the M1 Max.
- **Mask geometry**: the "grow" scalp+halo mask (crown above brow line + dilated
  halo, minus facial features) correctly defines where added hair should go.
- **Swappable-backend architecture** works — model is a pluggable piece.

## What's NOT proven / open ❌

- **Generative quality**: SD1.5+LCM is **too weak to synthesise convincing new
  hair**, even with a correct mask — it filled the scalp with skin-toned mush.
  This is a *model* limitation (expected), not a pipeline one. Needs Flux/Qwen/etc.
- **Temporal consistency** — the central question — is **still unanswered.** The
  test clip was a near-bald/shaved head, so there was no substantial hair edit to
  judge consistency of, and a still-repeat smoke clip didn't test rotation.
- **Mask-based ≠ generative product path.** Mask-based inpaint can only restyle
  *existing* hair; adding hair to a bald head needs an instruction model (Flux/Qwen)
  or the 3D approach. The mask work was a local-model stopgap.

## Key learnings

- The bald test clip exposed that **mask-based local SD1.5 can't add hair onto bare
  scalp** — which motivated both the geometry mask AND the move toward
  instruction-based / 3D generative.
- "It ran" ≠ "it worked" — always *look at the frames*.
- Bugs found & fixed along the way: aspect-ratio squish (output forced to 512²),
  side-by-side hstack size mismatch, missing `peft` for LCM-LoRA.

## Notable: the bald clip is the *ideal* testbed for "draw hair on bald"

The user's canonicalisation idea (make everyone bald → draw hair on a clean canvas)
is a published method — **Stable-Hair** (AAAI 2025). A bald/shaved capture is the
*best-case* input for the "generate hair onto a canonical bald head" half.
