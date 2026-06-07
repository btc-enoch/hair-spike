# 05 — Privacy & Data Retention

The app sends images of users' **faces** to a generator. Where that runs
determines whether the data is retained / trained on. (Note: the pipeline extracts frames
locally and uploads *stills*, not the video file — but face images leave the
machine either way.)

## Black Forest Labs (BFL) — the Flux first-party API

**Default: retains input images AND trains on them.** From their privacy policy:

> "...prompts and other content that is submitted to the Services, such as your
> **image files**... We collect this information to... **develop, train and
> improve**... our **AI models**."

- Their standard terms grant a licence to use input/output to train.
- **Zero-data-retention is enterprise-only** — not the default for a self-serve key.
- SOC 2 / ISO 27001 / GDPR compliant — but that's *security*, not "we delete it."

Sources: bfl.ai/legal/privacy-policy, /terms-of-service, /developer-terms-of-service

## "Flux" the model keeps nothing — the host does

"Flux" is just weights; retention is entirely about **who runs it**:

- **via BFL direct** → retain-and-train default (above).
- **via Replicate** → Replicate's terms (generally don't train on inputs; you can
  delete predictions).
- **on your own GPU** → nobody keeps anything, by construction.

## Implication for us

| Clip type | Guidance |
|---|---|
| Throwaway test clip (spike) | Sending a few frames to a cloud API is low-stakes. Fine. |
| Real users' faces (product) | BFL default "retain + train on selfies" is a serious problem. Use enterprise zero-retention, or — cleaner — **self-host open weights**. |

This is the privacy argument that makes **Qwen-Image-Edit self-hosted** attractive
for the product: commercially licensed *and* faces never leave your infrastructure
(zero retention by construction). See [04-model-options.md](04-model-options.md).

## Cloud vs local (recap)

| | Cloud API | Local / self-host |
|---|---|---|
| Privacy | faces leave your machine | faces never leave |
| Cost | per-call, forever | free per run after setup |
| Speed | fast (cloud GPUs) | slower on a Mac; needs real GPU for prod |
| Docker on macOS | works (light container) | **no GPU passthrough** — must run natively |
