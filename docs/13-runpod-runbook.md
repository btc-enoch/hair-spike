# 13 — RunPod Setup Runbook (on-demand GPU for the bake pipeline)

Spin up a cheap NVIDIA GPU, port our stack, run a bake, tear down. Goal:
cents-per-experiment, only pay while it runs.

> **GPU choice:** RTX 4090 (24GB) is plenty for Brush GS + the bake. Don't rent an
> H100 — ~5× the cost for no benefit here. Community Cloud ≈ $0.34–0.50/hr;
> Secure Cloud ≈ $0.69/hr.

---

## 0. Prereqs (once)
- RunPod account + ~$10 credit.
- `BFL_API_KEY` (editing still goes through BFL for now; self-host Flux later).
- Our code in a **git repo** so the pod can `git clone` it. (Brush itself is cloned
  fresh on the pod; we only ship our scripts + the `apps/brush-orbit` crate + a
  capture.) See "Porting our code" below.

## 1. Launch the pod
RunPod console → **Deploy** →
- GPU: **RTX 4090**, **Community Cloud** (cheapest), **On-Demand** (per-second).
- Template: **RunPod PyTorch 2.x** (Ubuntu 22.04 + CUDA 12.x).
- Container/volume disk: **~60 GB** (Brush build + python + models).
- Enable **SSH**. Deploy.

## 2. Connect
```bash
ssh root@<POD_IP> -p <PORT> -i ~/.ssh/id_ed25519     # details shown in RunPod UI
# or use the web terminal / Jupyter from the console
```

## 3. System deps (incl. Vulkan — Brush is wgpu, runs on Linux via Vulkan)
```bash
apt-get update && apt-get install -y \
  ffmpeg git build-essential cmake curl \
  libvulkan1 vulkan-tools mesa-vulkan-drivers
vulkaninfo 2>/dev/null | grep -i deviceName   # MUST show the NVIDIA GPU
```
If `vulkaninfo` doesn't list the GPU, the NVIDIA Vulkan ICD is missing — usually
fixed by matching driver/`nvidia` packages, or fall back to the CUDA GS stack
(gsplat/nerfstudio) for training.

## 4. Rust + build Brush
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
git clone https://github.com/btc-enoch/hair-spike.git ~/hair-spike   # public, no auth      # our scripts + apps/brush-orbit crate
git clone --depth 1 https://github.com/ArthurBrussee/brush.git ~/hair-spike/brush
# add our brush-orbit crate into the brush workspace:
cp -r ~/hair-spike/brush-orbit ~/hair-spike/brush/apps/brush-orbit
#   + add "apps/brush-orbit" to brush/Cargo.toml [workspace].members  (one line)
cd ~/hair-spike/brush
cargo build --release -p brush-app -p brush-orbit   # builds `brush` + `brush-orbit`
```
(Binaries land in `brush/target/release/{brush,brush-orbit}`.)

## 5. Python env
```bash
cd ~/hair-spike
python -m venv .venv && . .venv/bin/activate
pip install torch torchvision diffusers transformers peft pillow requests pycolmap
```

## 6. Upload a capture & run
```bash
# from your Mac, push a capture up:
scp -P <PORT> in/IMG_8057.mp4 root@<POD_IP>:~/hair-spike/in/

# on the pod:
cd ~/hair-spike && . .venv/bin/activate && export BFL_API_KEY=...
./recon_run.sh in/IMG_8057.mp4 7000 80 cloud1                       # reconstruct (GPU)
python bake.py recon/runs/cloud1 "thick brown wavy hair" cloud1 --iters 7000   # bake
# fast iteration: lower res — edit make_turntable/brush args + brush --max-resolution 640
```
> **Linux path tweaks:** our scripts hardcode a couple of mac paths
> (`/opt/homebrew/bin` for ffmpeg, the `.venv` path). On Linux, ffmpeg is on PATH
> and the venv is local — adjust those two spots (or set `PATH`/`$ROOT` accordingly).

## 7. Download results
```bash
# from your Mac:
scp -P <PORT> root@<POD_IP>:'~/hair-spike/outputs/videos/*.mp4' ./
```

## 8. TEAR DOWN (stop the meter)
- **Stop** the pod → keeps the disk for a fast restart (small storage charge).
- **Terminate** → deletes everything, **zero** ongoing charge.
- ⭐ **Save a Template / snapshot after step 5** so next time you skip the ~15-min
  build and go from deploy → running in ~2 min.

---

## Cost per run
- RTX 4090 ≈ **$0.40/hr**.
- One-time setup (deps + build Brush): ~15–20 min ≈ **$0.10–0.15** (skip next time via template).
- Per bake experiment: ~15–30 min GPU ≈ **$0.10–0.20** (+ BFL edits: ~$0.04 × #views,
  or **$0 once we self-host the editor**).
- So **experiments are cents.** Forgetting to stop the pod is the real cost risk —
  prefer **Stop/Terminate** or move to **Modal serverless** (scale-to-zero) later.

## What's still on BFL vs self-hosted
- **Now:** editing via BFL API (needs only the key + network). Simplest.
- **Optimization (later):** self-host Flux Kontext on the same pod (download weights
  + diffusers/ComfyUI) → no per-edit fee, faster loop. Bigger setup; do it once the
  pipeline's settled.

## Porting our code (prep)
Make `~/hair-spike` a git repo with a `.gitignore` excluding build/data junk:
```
brush/            # cloned fresh on the pod (huge)
.venv/
recon/
outputs/
in/*.mp4
*.ply
*.mp4
```
…but **keep** `brush-orbit/` (copy of `brush/apps/brush-orbit` source) so the pod
can drop it into the freshly-cloned Brush workspace. Then the pod just needs:
scripts (`*.py`, `*.sh`) + `brush-orbit/` + `docs/`.
