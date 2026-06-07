# 04 — Generative Model Options

The image model is a **pluggable backend** (see `../hairswap.py`). Claude is *not*
an option for generation — Anthropic models are text + vision-input only; Claude's
role is NLU (voice→spec) and vision QA. See [02-architecture.md](02-architecture.md).

## A. Open-weights instruction editors (ownership + self-host)

- **Qwen-Image-Edit (2511)** — **the strategic standout.** Top open editing
  quality, strong identity/character preservation (exactly our risk area), and
  **Apache-2.0** → commercially shippable AND self-hostable. The *only* option
  that is both commercially usable and private-by-self-hosting. Big (~20B) → slow
  locally, wants a real GPU for production.
- **Flux.1 Kontext [dev]** — strong, but **non-commercial licence** (fine to test,
  can't ship).
- **LongCat-Image-Edit** — high-precision instruction edits, preserves non-edited
  regions.

## B. Hosted APIs (best raw quality, no ownership, retention concerns)

- **Google Nano Banana Pro / Nano Banana 2** (Gemini image) — **#1 on editing
  leaderboards**, excellent identity preservation. Cloud only.
- **OpenAI GPT Image 2 / 1.5** — strong at complex spatial instructions.
- **Black Forest Labs Flux Kontext Pro / Max** — hosted (better) Flux tiers.
  ⚠️ See [05-privacy-and-data.md](05-privacy-and-data.md) — BFL trains on inputs by default.
- **ByteDance Seedream / SeedEdit** — also top-ranked.
- **Aggregators (Replicate, fal.ai, Runware)** — one key → many models incl. open
  ones. Pragmatic path: test in cloud now, move the same open weights to your own
  GPU later. No lock-in.

## C. Hair-specialist models

- **Stable-Hair** (AAAI 2025, open) — **exactly our canonicalisation idea, as a
  published method:** stage 1 a "Bald Converter" removes existing hair → bald
  canvas; stage 2 transfers the target hairstyle. Reference-image driven (not text),
  image-based.
- **HairFastGAN** (fast), **Barbershop** (high-q, slow), **HairCLIP** (text) — GAN
  hair transfer. Best on aligned frontal faces; weaker on arbitrary video poses;
  finicky setup.

## D. Local quality-upgrade, mask-based

- **SDXL-inpaint + IP-Adapter + ControlNet** — big step up from SD1.5, open,
  permissive, runs on the M1 Max (~30–60s/frame). Still mask-based.
- **SD1.5 + LCM-LoRA** — what the spike used. Fast (~3.3s/frame on M1 Max) but
  **too weak to synthesise convincing new hair** (see [08-spike-status.md](08-spike-status.md)).

## Decision guide

| Priority | Pick |
|---|---|
| Own it + ship commercially | **Qwen-Image-Edit (Apache-2.0)** |
| The bald→hair architecture, prebuilt | **Stable-Hair** |
| Fastest "is quality even there?" gut-check | **Nano Banana** or **Flux Kontext** via aggregator |
| Stay in current pipeline, just better | **SDXL-inpaint + IP-Adapter** |

## Current direction

- For **product**, leaning **Qwen-Image-Edit** (commercial licence + self-host =
  privacy + ownership). Quality is competitive with Flux Kontext; the best closed
  model (Nano Banana Pro) is a notch above but cloud-only/retain-and-train.
- For **cloud gut-checks**, Flux Kontext or Nano Banana via an aggregator.
- No image editor solves **temporal consistency** — that's a pipeline/3D problem,
  not a model choice.
