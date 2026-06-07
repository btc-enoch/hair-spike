# 01 — Product Vision & Scope

## The concept

A user can:
1. **Speak** to the app and describe the hairstyle they want.
2. Record a short **~5-second rotate selfie video** (turning their head).
3. The app applies the requested hairstyle **generatively** and lets them see
   the new look **from every angle**.

## Scope decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Platform | **iOS native** | Best camera/AR access, on-device ML, strong real-time perf |
| Stage | **Real product MVP** | Foundations that can grow, not just a throwaway demo |
| Processing model | **Capture-then-process** (not live 30fps) | Live per-frame generative isn't production-ready; removing the real-time constraint massively improves quality and feasibility |
| Style application | **Generative** (any style from a prompt) | The differentiator and the market white space. Not a curated 3D-asset library. |

## How the scope evolved

1. **Initial ask:** live, real-time hairstyle on a selfie video feed.
   - *Reality:* full per-frame generative restyle on live 30fps video is **not
     production-ready in 2026** — too slow on-device, and flickers frame-to-frame.
2. **Reframe (user):** speak → record a 5s rotate → process the clip.
   - *This removed the hardest constraint (real-time).* The rotation also gives
     multi-angle input, which is exactly what 3D-aware methods want.
3. **Refinement:** capture once → build a reusable model → interact repeatedly.
4. **Constraint locked (user):** **it has to be generative** — no asset library.

## What "good" looks like for the MVP

- Speak a style → see yourself wearing it, from every angle, in seconds.
- Identity clearly preserved (it still looks like *you*).
- Consistent as the head turns (no flicker/morph).
- Works from a casual phone capture (not a studio).

## Known hard problems (carried forward)

- **Temporal consistency** across the rotation — *still the central open risk.*
- **Dramatic length changes** (e.g. long→buzz, bald→long) need inventing
  unseen geometry/background.
- **Identity preservation** — keeping the face unmistakably the user.
- **Cost per generation** — generative video is expensive; see
  [06-unit-economics.md](06-unit-economics.md) and [07-cost-strategy.md](07-cost-strategy.md).
