# 07 — Cost Strategy: Minimise Cost/Clip

**Current strategy (decided): minimise cost/clip.** The model showed it moves
break-even more than any other lever, and that high cost/clip is fatal at any scale.

## The cost equation = a stack of multipliers

cost/clip ≈ **frames × steps × resolution × model-size ÷ (GPU throughput-per-$)**

| Lever | Naive | Target | Cut | Helps consistency? |
|---|---|---|---|---|
| Frames generated | 150 | ~8–15 (keyframe) → ~1–3 (3D) | 10–50× | ✅ (3D) |
| Steps (diffusion iters) | ~30 | 4–8 (distilled LCM/Turbo) | 4–8× | — |
| Resolution | native high-res | diffuse low + cheap upscale | 2–4× | — |
| Area | full frame | crop to head, composite back | 2–3× | — |
| GPU/billing | reserved 24/7 | serverless + spot + batching | 2–5× on $ | — |

Stacked: ~$1.00 → **~$0.02–0.05/clip**.

## Build order (highest leverage first)

1. **Instrument cost/clip** — can't minimise what you don't measure.
2. **Frames** (the 10–50× lever): **generate-once-render-many (3D)** is the target
   — it cuts cost *and* fixes consistency in one move. (Keyframe+interpolation is a
   2D stopgap but depends on consistent keyframes.)
3. **Steps** — distillation (already proven via SD1.5+LCM locally).
4. **Crop-to-head + low-res-then-upscale.**
5. **Serverless + batching** at deploy time.

## Where 3D lands (all else equal)

3D ≈ **$0.02/clip** → break-even **~96k users** (vs ~198k at $0.10), and **100k
users flips from −$20k/mo to +$1.7k/mo profit.**

## Diminishing returns — the floor

Past 3D, cutting cost/clip barely moves subscription break-even:

| Effective $/clip | Break-even |
|---|---|
| $0.020 (3D, 1 style) | 96k |
| $0.008 (amortised, 5 styles/capture) | 89k |
| $0.0027 (+ spot GPU) | 86k |

So **3D is roughly where this lever maxes out** for the *subscription arithmetic*.

## But cheaper clips unlock two *structural* wins (worth pursuing)

The reason to keep cutting cost past 3D — via **free-lunch cuts only** (no quality
loss): amortise per-capture work across styles, spot GPUs, batching, crop-to-head.

1. **Ad-funded free tier becomes viable.** Ads needed to cover one free user/mo:
   - $0.10/clip → 7.5 ads (unworkable)
   - $0.02/clip → 1.5 ads
   - **~$0.005–0.008/clip → <1 ad** → a single rewarded ad covers a free user's
     entire monthly GPU cost → **flips the free tier from pure loss to break-even.**
     This neutralises the biggest drag in the model.
2. **Engagement becomes ~free.** Amortisation makes "try another style" nearly
   free → enables generous near-unlimited try-on UX → drives conversion/retention
   (the lever that *does* move break-even a lot).

> Net: pursue free-lunch cuts NOT for the direct break-even gain (small past 3D)
> but because they cross the **ad-funding threshold** and make engagement free —
> which feeds the conversion + ad lever that actually breaks the deadlock.

## Hold in reserve (these throw away quality)

Fewer diffusion steps, smaller models, lower resolution — use only if free-lunch
cuts aren't enough.

## Amortisation = why the 3D model is the cache boundary

3D cost decomposes into **per-capture reconstruction (~$0.015, once)** +
**per-style hair-gen (~$0.005)**. The persisted 3D model is the cache boundary:
trying N styles = 1 reconstruction + N cheap hair-gens. See [02-architecture.md](02-architecture.md).

## Strategy sequence

1. **Now:** get cost/clip to 3D-level (~$0.02). Doubles as the consistency fix.
2. **Then the lever shifts** to conversion (5%→10% nearly halves break-even again),
   ARPU (credits/bundles), ad-funded free tier, and/or B2B2C.
