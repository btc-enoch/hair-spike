# 14 — Production Architecture (optimised for speed)

The speed-optimised production design. Core principle: **split the expensive-once
work from the latency-critical loop; make the build feed-forward; push interaction
on-device; isolate the single generative round-trip and make it few-step on a warm
GPU.**

> Status: target design. The current spike (per-scene Brush optimisation + 2D bake)
> proved *feasibility*; this is the *speed* target. The upgrade path is at the end.

## The two-phase split (foundation of speed)

```
── ONBOARDING (once per user) ───────────────────────────────────────────
 capture 5s ─▶ feed-forward reconstruction (GPU, ~1–5s) ─▶ 3D head model
               (single forward pass, NOT per-scene optimisation)         │
                                                                          ▼
                                                   stored + pushed to device (CDN)

── INTERACT (every "try a style") — latency critical ────────────────────
 voice ─▶ STT + Claude NLU (~0.5–1s) ─▶ style spec
                                          │
        ┌──────────────────────────────────┴─────────────────────────────┐
        ▼ cached / on-device asset                     ▼ new generative style
   INSTANT render on-device                    warm GPU, few-step gen (~2–4s)
   (model already on the phone)                → 3D hair asset → render on-device
```

Build is amortised across every style; only a *genuinely new* style touches the GPU.

## Speed levers (priority order)

| # | Lever | Why it's fast |
|---|---|---|
| 1 | **Build once, reuse** | the expensive reconstruction is amortised over all styles |
| 2 | **Feed-forward reconstruction** | one forward pass (~s) vs per-scene optimisation (min) — the build-speed unlock |
| 3 | **On-device rendering** | model lives on the phone → spin/browse/asset-swap is real-time, zero round-trip (Snap-AR pattern) |
| 4 | **Warm GPU pool** | keep-warm instances kill cold starts — the #1 latency killer |
| 5 | **Few-step distilled generation** | 4–8 steps not 30 → ~5–8× faster per generate |
| 6 | **Cache + precompute** | per-user model + per-(user,style) assets cached; precompute top-N popular styles during onboarding |
| 7 | **Tiered / streaming UX** | instant on-device preview (asset/low-res) → refine with server "hero" → perceived latency ≈ 0 |

## Latency budget — "try a style"

| Step | Cached / asset | New generative style |
|---|---|---|
| Voice → spec (streaming STT + Claude) | ~0.5–1s | ~0.5–1s |
| Apply hair | instant (on-device asset) | ~2–4s (warm GPU, few-step) |
| Render turn | real-time on-device | real-time on-device |
| **Total** | **~1s** | **~3–5s** |

## Services

| Service | Role | Speed notes |
|---|---|---|
| Mobile app | capture, voice, **on-device 3D render**, UI | renders the model locally |
| STT + Claude NLU | streaming voice → structured style spec | sub-second, streaming |
| Reconstruction | feed-forward 3D head build (onboarding) | GPU **warm pool** |
| Hair-gen | few-step generative hair (per style) | GPU **warm pool**, scale-to-zero off-peak |
| Model/asset store | 3D models + hair assets | object storage + **CDN** to device |
| Cache | per-user model, per-(user,style) asset, global popular | hit path = instant |
| Orchestration/queue | async jobs, precompute | streams results to client |

## The single biggest decision: render on device, generate on server
Download the user's 3D model to the phone once. Then **browsing and swapping
cached/asset styles is instant and free**, and the server GPU is touched **only**
for a genuinely new style. This confines all latency *and* cost to the rare
generative moment and makes the common path feel native.

## Cost ↔ speed alignment
The speed design *is* the cost design (see [07](07-cost-strategy.md), [13 economics]):
- Build once → amortised.
- On-device render → engagement is free (no GPU per spin).
- Few-step + warm-but-scale-to-zero → cheap per generate.
- Cache/precompute → repeat styles cost nothing.
Net per-style: **cents** on the new-style path, **free** on the cached/on-device path.

## Upgrade path from the current spike

| Component | Spike (now) | Production (fast) | Gap |
|---|---|---|---|
| Reconstruction | per-scene Brush optimisation (~min) | **feed-forward** (~s) | newer, lower-fidelity — validate speed/quality tradeoff |
| Hair application | 2D edit → multi-round 3D bake (slow) | **3D-native hair** (HAAR-style) or **cached assets** → renderable | 3D-hair gen is frontier (see [11]/[12]) |
| Rendering | server-side brush-orbit | **on-device** GS/strand render | port renderer to mobile (Metal/Vulkan/WebGPU) |
| Editor | BFL API per call | **self-hosted few-step**, warm pool | no per-call fee, no cold start |
| Delivery | scp/manual | model+assets via **CDN to device** | standard infra |

## Honest caveats
1. **Feed-forward reconstruction** trades fidelity for speed — the quality bar must be
   validated (the spike showed per-scene quality is already capture-bound).
2. **3D-native hair generation** (the renderable-asset path that makes interaction
   instant) is the frontier piece — control/maturity are open (see [11](11-spike2-generative-tests.md)).
3. **On-device rendering** means porting the splat/strand renderer to mobile — real
   engineering, but the biggest single latency + cost win.
4. The spike validated the *pipeline*; this design is the *speed/scale* target, and
   each upgrade above is its own build.

## TL;DR
Onboard once with a **feed-forward** build (~seconds). Put the **model on the device**
so browsing is instant and free. Reserve a **warm, few-step GPU** for the rare new
generative style (~3–5s). **Cache and precompute** the rest. That's "as fast as
possible" without betting on anything that isn't on a credible near-term path.
