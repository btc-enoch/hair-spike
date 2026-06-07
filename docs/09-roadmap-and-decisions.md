# 09 — Roadmap & Decisions

## Decisions log (as of 2026-06-05)

| # | Decision | Notes |
|---|---|---|
| 1 | **iOS native**, real-product MVP | — |
| 2 | **Capture-then-process**, not live 30fps | Live per-frame generative isn't production-ready |
| 3 | **Generative** styles, not an asset library | The differentiator; locked by the user |
| 4 | Architecture = **capture → build 3D head model → interact generatively** | 3D model = cost + consistency + canonicalisation keystone |
| 5 | **"Generative" = generate-on-canonical-views → bake into 3D**, NOT per-frame | Per-frame is the ~$1/clip flickery path, ruled out |
| 6 | **Strategy: minimise cost/clip** | Highest-leverage; target ~$0.02 via 3D |
| 7 | Product model leaning **Qwen-Image-Edit, self-hosted** | Apache-2.0 (commercial) + privacy (faces never leave) |
| 8 | Don't send real users' faces to BFL | Default retains + trains on inputs |

## The core R&D bet

> **Can we bake a generative hair edit into a 3D head model so it stays coherent
> from every angle?** This is the frontier piece and the make-or-break. There's no
> asset-library fallback once generative is required.

## Next steps

### Spike 1 — Reconstruction (mature, foundational, do first)
- Take the existing 5s rotate clip, run it through a **Gaussian-Splatting**
  pipeline.
- **Question:** does a casual 5s phone capture produce a good-enough 3D head model?
- Low risk; it's the input to the hard test.

### Spike 2 — Generative bake (the real bet, right after)
- On that 3D model: render canonical view(s) → generative hair edit (Flux/Qwen) →
  **bake into the model** → render the turn.
- **Question:** is the rendered turn consistent and identity-preserving?
- This is where the architecture lives or dies — test it early.

### Parallel / smaller
- **Instrument cost/clip** in the pipeline (GPU-seconds → $/clip) so every cost
  lever reports before/after.
- **Quality gut-check**: run the existing clip through **Flux Kontext** (cloud) or
  **Qwen-Image-Edit** to see the quality ceiling (use a stock face if avoiding
  sending the real clip to a retain-and-train API).
- **Voice→spec** step with Claude (NLU) — small, cheap, well-understood.

## Open questions to resolve

- Can casual captures reconstruct well enough? (Spike 1)
- Does generative-into-3D hold consistency across angles? (Spike 2)
- Real per-capture vs per-style cost split (benchmark once 3D pipeline exists) —
  validates the ~$0.015 recon / ~$0.005 hair-gen assumption.
- Which generator for production (Qwen self-host vs others) — pending quality test.
- Business model past cost: conversion, ARPU/credits, ad-funded free tier, or B2B2C.

## Longer-term economics path (after cost/clip is handled)

1. **Now:** cost/clip → ~$0.02 (3D). Break-even ~96k users; 100k profitable.
2. **Then:** conversion (5%→10% nearly halves break-even), ARPU (credits/bundles),
   ad-funded free tier (unlocked once cost/clip ~$0.005–0.008), and/or B2B2C
   (breaks even at ~2 orders of magnitude fewer customers).
