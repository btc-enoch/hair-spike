# 02 — Architecture: Capture → Build → Interact

The product is three phases, with a **3D head model** as the persistent artifact
that lives between them.

```
 1. CAPTURE        2. BUILD                    3. INTERACT (loop)
 5s rotate    →    reconstruct 3D head    →    "show me a bob"  → render
 + voice           (expensive, ONCE)           "now blonde"     → render
                   = your personal model        "longer"         → render
                          │                          ▲
                          └──── persisted ───────────┘
                               (saved to the user's account)
```

## What the "3D model" is

Not a CAD mesh — a photoreal, view-from-any-angle reconstruction. Practical 2026
representations:

- **3D Gaussian Splatting (3DGS)** — millions of tiny 3D blobs (position, colour,
  opacity, size). Trains in seconds–minutes from multi-view, renders photoreal in
  real time. **Likely default.**
- **Parametric head (FLAME / 3DMM)** — a riggable statistical head mesh. Clean and
  controllable, lower realism alone.
- **Hybrid (FLAME + attached Gaussians)** — rigged mesh drives the gaussians:
  photorealism **and** control. Sweet spot for an app.

## How the model is built (phase 2)

```
5s rotate video
  → extract frames (~30–60)
  → estimate camera pose per frame (structure-from-motion / learned pose net)
  → detect face landmarks / align
  → FIT the representation (optimise Gaussians/FLAME so re-render matches frames)
  → = the head model (splat/mesh artifact + camera trajectory)
```

This fit is the **expensive, once-per-capture GPU step** (~20–60s). Reconstruction
and rendering are **mature**; this part is low-risk.

## How styles get applied (phase 3) — MUST be generative

Two philosophies; the user has chosen the generative one:

| | 3D hair assets (library) | **Generate-on-canonical → bake into 3D** |
|---|---|---|
| Source of styles | curated grooms | **any style from a prompt** |
| Consistency | rock-solid | structural (rendered from one model) |
| Cost per style | ~free, instant, can run on-device | ~seconds + a few cents, server GPU |
| Maturity | shippable today | **research frontier** |
| Chosen? | ❌ | ✅ (generative is required) |

**Generative path:** render a few **canonical views** from the head model →
run the generative editor (Flux/Qwen/etc.) on those views → **bake** the edit
back into the 3D model → render the full turn (cheap rasterisation, not diffusion).

> **Critical distinction:** "generative" here means **generate on a few canonical
> views and bake into 3D** — NOT generate every frame. Per-frame generation is the
> ~$1.00/clip, flickery path we ruled out. The 3D model is what makes generative
> affordable.

## Where the 3D model sits (request flow)

```
 iOS app ──capture(5s rotate)+voice──▶ BACKEND
                                         │
   voice→text (STT)                      ▼
        │                     ┌──────────────────────┐
        │                     │ RECONSTRUCTION (GPU)  │ ← EXPENSIVE, ONCE/capture
        │                     │ frames→poses→fit 3DGS │
        │                     └──────────┬───────────┘
        │                                ▼
        │                     ┌──────────────────────┐
        │                     │  3D HEAD MODEL        │ ← persisted (object store,
        │                     │  (splat/mesh+cameras) │    keyed by captureID, TTL)
        │                     └──────────┬───────────┘
        ▼                                │  ◀── reused for EVERY style ──┐
 ┌─────────────┐   style spec            ▼                              │
 │ Claude NLU  │ ─────────────▶ ┌──────────────────────┐                │
 │ text→spec   │                │ HAIR-GEN (GPU)        │ ← CHEAP, per style
 └─────────────┘                │ edit canonical→bake3D │                │
                                └──────────┬───────────┘                │
                                           ▼                            │
                                ┌──────────────────────┐                │
                                │ RENDER (GPU, cheap)   │ ──────────────┘ "try another"
                                │ rasterise the turn    │
                                └──────────┬───────────┘
                                           ▼
                               output clip ─▶ iOS app (+ cache)
```

## Why the 3D model is the keystone

One component solves three problems at once:

- **Cost / amortisation** — reconstruction (the expensive bit) is paid **once per
  capture**; trying 10 styles = 1 reconstruction + 10 cheap hair-gens + 10 renders.
- **Consistency** — every output frame is rendered from **one** model → hair
  physically can't flicker across the turn.
- **Canonicalisation** — you edit the **canonical** head once, centrally, instead
  of 150 frames. (This is also where the "bald canvas" idea lives.)
- **Free re-rendering** — any resolution, framerate, or new angle is cheap raster.

## Role of Claude in the architecture

Claude does **not** generate images (Anthropic models are text + vision-*input*
only). Its two roles:
1. **Voice → structured style spec** (NLU): "wavy shoulder-length bob, curtain
   bangs, warm brown" → `{length, cut, bangs, colour, ...}`.
2. **Vision QA / judge:** look at output frames and score identity preservation,
   artifacts, cross-angle consistency (LLM-as-judge to automate quality checks).

## The core R&D bet

Everything except one piece is mature or solved. The make-or-break:

> **Baking a generative hair edit into the 3D model so it stays coherent from
> every angle** — including the back of the head barely seen in the capture.
> There is no asset-library fallback once "generative" is required.

De-risk order: **(1) reconstruction spike** (mature, foundational) →
**(2) generative-bake spike** (the real bet). See
[09-roadmap-and-decisions.md](09-roadmap-and-decisions.md).
