# Hair Try-On App — Project Docs

A voice-driven AI hairstyle try-on app: the user **speaks** the style they want,
records a short **5-second rotate selfie video**, and the app applies a
**generative** hairstyle that they can view from every angle.

> Status: **exploration / spike phase.** Working code lives in `../hairswap.py`
> (pipeline) and `../model.py` (unit economics). These docs capture the thinking,
> decisions, and findings as of **2026-06-05**.

## Index

| Doc | What's in it |
|---|---|
| [01-product-vision.md](01-product-vision.md) | The concept, scope decisions, what we're building toward |
| [02-architecture.md](02-architecture.md) | Capture → build 3D model → interact; where the 3D model fits; the generative requirement |
| [03-competitive-landscape.md](03-competitive-landscape.md) | Who's in market, where the white space is |
| [04-model-options.md](04-model-options.md) | Generative models surveyed, licensing, recommendations |
| [05-privacy-and-data.md](05-privacy-and-data.md) | Cloud data retention (BFL trains on inputs), local vs cloud |
| [06-unit-economics.md](06-unit-economics.md) | Cost/clip, break-even model, scenarios |
| [07-cost-strategy.md](07-cost-strategy.md) | Minimise cost/clip: 3D, amortisation, ad-funding, diminishing returns |
| [08-spike-status.md](08-spike-status.md) | What's been built and tested, what's proven vs unproven |
| [09-roadmap-and-decisions.md](09-roadmap-and-decisions.md) | Decisions log + next steps |
| [10-spike1-results.md](10-spike1-results.md) | **Spike 1 done (2026-06-06):** local 3D reconstruction works; iterations don't help, capture is the ceiling |
| [11-spike2-generative-tests.md](11-spike2-generative-tests.md) | **Spike 2 (2026-06-07):** generative edit quality + identity ✅; per-frame consistency ❌ → 3D bake mandatory. Path = iterative bake (option 2) |
| [12-spike2-option2-scope.md](12-spike2-option2-scope.md) | **Scope for the iterative 3D bake** — loop, cloud stack (nerfstudio/igs2gs + Flux), risks, cost/time, decisions needed |
| [13-runpod-runbook.md](13-runpod-runbook.md) | **RunPod on-demand GPU runbook** — launch RTX 4090, port Brush+pycolmap+scripts, run a bake, tear down; ~cents/run |

## The one-paragraph summary

Build for **iOS**, target a **real MVP**. The output must be **generative**
(any style from a prompt, not a pre-made asset library). The technically- and
economically-correct architecture is **capture → build a 3D head model once →
interact by generatively restyling that model**. The 3D model is the keystone:
it is simultaneously the **cost lever** (build once, reuse across every style),
the **consistency fix** (render the turn from one model so hair can't flicker),
and the **canonicalisation surface** (edit once, centrally). The make-or-break
technical bet is **baking a generative hair edit into the 3D model so it stays
coherent from every angle** — that's the frontier piece and the thing to
de-risk first.
