# 11 — Spike 2 Tests: Generative Hair (2026-06-07)

**Goal:** is generative hair viable for the product — good quality, identity-
preserving, and *consistent across the turn*? Tested cheaply before any 3D-bake build.

## Test A — single-frame edit (stock face, BFL Flux Kontext)
`hairedit.py` on a stock frontal portrait, two dramatic styles.
- **Result: PASSED, strongly.** Photoreal new hair; identity fully preserved
  (same face/eyes/smile/skin/background) through big changes (curly→platinum bob;
  curly→long black + bangs). ~$0.04/edit, ~2s.
- **Conclusion: the generative edit itself is excellent.** (Flux Kontext is strong here.)

## Test B — per-frame edit across the real rotate (IMG_8057, bald → add hair)
`hairswap.py --backend bfl`, 16 frames of the turn, same style + fixed seed, each
frame edited **independently**, reassembled into a side-by-side video.
- **Per-frame quality: excellent** — every frame photoreal, hair convincingly added
  to the bald head (even profiles), clearly the same person.
- **Consistency: FAILS (as predicted).** Each frame is a *different haircut* —
  length, parting, and hairline change frame-to-frame because each edit is
  independent. In motion the hair **flickers / swims**.
- Cost ~$0.64 (16 × ~$0.04). Outputs: `outputs/videos/perframe_bfl_*.mp4`.

## The crux finding
> **Naive per-frame generative = great stills, unusable video.** The generative
> quality is there; **multi-view consistency is the real problem.** A consistency
> mechanism is therefore **mandatory** — which is exactly the case for the
> **generate-once → bake-into-3D** architecture (render every frame from ONE model
> so the hair can't change).

## Spike 2 status
- Step 1 — generative quality + identity: ✅ **passed**
- Step 2 — per-frame consistency: ❌ **confirmed absent** → consistency mechanism mandatory
- Step 3 — achieving consistency: the frontier R&D, still ahead

## Step 3 options (achieving multi-view consistency)
1. **Reference-conditioning** — generate the front once, anchor other views to it
   (IP-adapter / multi-reference). Cheapest; an *enabler* for cleaner bakes.
2. **3D bake (iterative dataset-update)** — render views from the 3D model, edit
   with the 2D diffusion editor, update the model toward the edits, repeat until it
   converges to a consistent 3D edit. This is the **Instruct-NeRF2NeRF /
   GaussianEditor / Instruct-GS2GS** family. Reuses our reconstruction + Brush +
   Flux stack; yields a reusable consistent 3D model. **Recommended path.**
3. **Video-diffusion / 3D-native generative hair** — temporally consistent by
   design, but heaviest, less controllable, and abandons the reusable-3D-asset
   architecture.

## Decision (2026-06-07): pursue **Option 2** (iterative 3D bake), with Option 1 as
an enabler for cleaner inputs. Caveats: it's genuine R&D, **cloud-GPU work** (the
iterative edit+retrain loop is far too slow on the M1 Max), and "add hair to bald"
is a *large structural* edit — harder for these methods than recolor/restyle, so
quality is not guaranteed. Option 3 deferred (heavier, less controllable, no 3D asset).
