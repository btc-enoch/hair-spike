# 06 — Unit Economics

Model lives in `../model.py` (every assumption is a variable at the top — edit and
re-run). Numbers are illustrative 2026 ballpark, not a forecast.

## The structural problem

This app's fun is "try lots of styles," and **every try costs GPU money.** Unlike
normal software (usage ~free), here **engagement = cost**, so break-even is driven
by **cost-per-clip × clips-per-user**.

## Cost stack per clip

| Component | Smart 2D pipeline | Naive (150 frames) |
|---|---|---|
| GPU generation | ~$0.08 | ~$1.00 |
| Storage + bandwidth | ~$0.01 | ~$0.01 |
| Voice STT + Claude parse | ~$0.01 | ~$0.01 |
| **All-in per clip** | **~$0.10** | **~$1.02** |

## GPU pricing (2026)

- **AWS**: g5.xlarge (A10G 24GB) ~$1.01/hr; g6e.xlarge (L40S 48GB) ~$1.88/hr.
  Can't rent a *single* H100 (p5 = 8 GPUs, ~$6.88/hr each). AWS is 2–5× pricier
  than specialised clouds.
- **Specialised (single H100)**: RunPod ~$2.39–2.69/hr, Lambda ~$2.86/hr, Spheron
  spot ~$1.03/hr.
- **Serverless per-second** (Modal/RunPod): pay only while generating. **Right
  choice for bursty MVP traffic** — don't reserve a 24/7 box until volume is steady.

## Per-clip time (estimates, ~1024px)

| GPU | per frame | Naive (150 frames) | Smart (~15 keyframes) |
|---|---|---|---|
| H100 | ~8s (Flux) / ~12s (Qwen) | ~20–30 min/clip | ~2 min/clip |
| L40S | ~20s / ~35s | ~50–90 min/clip | ~5 min/clip |

**Frame count dominates everything.** Generating every frame is a latency + cost
bomb (and the source of flicker).

## Break-even model (base case)

Assumptions: $9.99/mo, Stripe 2.9%+$0.30, 5% free→paid conversion, 25 paid clips/mo,
1.5 free clips/mo, 8% monthly churn, $40k/mo fixed opex.

| Cost/clip | Contribution/paid user | Break-even | Op profit @ 100k users |
|---|---|---|---|
| **$1.00 (naive)** | −$15.60 | never (negative blend) | −$260k/mo |
| **$0.10 (smart 2D)** | $6.90 | **~198k users** | −$20k/mo |
| **$0.02 (3D)** | $8.90 | **~96k users** | **+$1.7k/mo** |

- LTV/paid: $86 ($0.10) → $111 ($0.02). Max CAC/paid: $29 → $37.
- **Max CAC per *signup* is only ~$1.44–1.85** (5% convert → 20 signups/payer).
  Paid acquisition likely *loses money* at consumer install costs ($2–5+) →
  growth must be organic/viral, not ad-bought.

## Sensitivity: break-even users (cost/clip × conversion)

| cost/clip | 3% | 5% | 8% | 12% |
|---|---|---|---|---|
| $0.04 | 206k | 110k | 65k | 42k |
| $0.07 | 313k | 141k | 78k | 48k |
| $0.10 | 650k | 198k | 97k | 57k |
| $0.20 | **neg** | **neg** | 526k | 151k |

Two lessons: **(1)** high cost/clip ($0.20 naive-ish) is unprofitable at *any*
scale — the free tier outweighs paid margin. **(2)** cost/clip and conversion are
the dominant levers.

## Pricing models considered

- **Subscription + hard cap** — workable default; never offer uncapped "unlimited"
  (whales bankrupt it).
- **Credits / bundles** — margin guaranteed per transaction; cleanest economics.
- **Ads alone** — a rewarded ad pays ~$0.01–0.05 vs ~$0.10 cost → doesn't cover
  generative cost *unless* cost/clip drops (see [07-cost-strategy.md](07-cost-strategy.md)).
- **B2B2C (salons/brands)** — best margins; bypasses consumer CAC/conversion;
  what Perfect Corp/ModiFace do.
