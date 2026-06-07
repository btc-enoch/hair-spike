#!/usr/bin/env bash
# One-shot pod setup. Run ON a RunPod Linux/CUDA box after (repo is public — no auth):
#   git clone https://github.com/btc-enoch/hair-spike.git && cd hair-spike && ./bootstrap.sh
# Installs deps, builds Brush + our brush-orbit (Vulkan), sets up the python env.
# Idempotent: safe to re-run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== [1/5] system deps (ffmpeg, build tools, Vulkan, egui/winit build libs) =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  ffmpeg git build-essential cmake curl pkg-config libssl-dev \
  libvulkan1 vulkan-tools mesa-vulkan-drivers \
  libxkbcommon-dev libwayland-dev libxcb-render0-dev libxcb-shape0-dev \
  libxcb-xfixes0-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev \
  libgl1-mesa-dev libegl1-mesa-dev libfontconfig1-dev

echo "== verify GPU visible to Vulkan (Brush is wgpu/Vulkan) =="
if vulkaninfo 2>/dev/null | grep -qi deviceName; then
  vulkaninfo 2>/dev/null | grep -i deviceName | head -1
else
  echo "  !! WARNING: Vulkan sees no GPU. Brush training/rendering will fail."
  echo "     Check the NVIDIA driver/Vulkan ICD, or switch training to the CUDA"
  echo "     GS stack (gsplat/nerfstudio)."
fi

echo "== [2/5] Rust toolchain =="
if ! command -v cargo >/dev/null 2>&1; then
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
fi
source "$HOME/.cargo/env"

echo "== [3/5] clone Brush + graft our brush-orbit crate =="
[ -d brush ] || git clone --depth 1 https://github.com/ArthurBrussee/brush.git brush
mkdir -p brush/apps/brush-orbit
cp -r brush-orbit/. brush/apps/brush-orbit/
grep -q '"apps/brush-orbit"' brush/Cargo.toml \
  || sed -i 's|"apps/brush-cli",|"apps/brush-cli",\n    "apps/brush-orbit",|' brush/Cargo.toml

echo "== [4/5] build brush (training bin) + brush-orbit (renderer) — first build ~10-15 min =="
( cd brush && cargo build --release -p brush-app -p brush-orbit )
echo "   binaries: brush/target/release/{brush,brush-orbit}"

echo "== [5/5] python env (inherits the pod's CUDA torch via system-site-packages) =="
[ -d .venv ] || python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q diffusers transformers peft pillow requests pycolmap

cat <<'NEXT'

== bootstrap complete ==
Run a bake:
  export BFL_API_KEY=<your key>
  # put a capture in in/ (scp it up, or use one in the repo)
  ./recon_run.sh in/<clip>.mp4 7000 80 cloud1
  .venv/bin/python bake.py recon/runs/cloud1 "thick brown wavy hair" cloud1 --iters 7000
  # masked variant (sharper face): remask_bake.py after a bake's edits exist
Download results from your Mac:
  scp -P <PORT> root@<IP>:'~/hair-spike/outputs/videos/*.mp4' ./
When done: STOP/TERMINATE the pod (or save a template to skip this build next time).

Note: for GPU-accelerated masking, remask_bake.py's device check is mps/cpu —
add a CUDA branch to use the pod GPU (cpu still works, just slower).
NEXT
