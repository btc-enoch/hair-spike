#!/usr/bin/env bash
# Local 3D head reconstruction pipeline (all on the Mac, GPU via Metal):
#   video -> frames -> pycolmap (camera poses) -> Brush (Gaussian Splatting) -> .ply
#
# NON-DESTRUCTIVE: each run writes to a unique recon/runs/<label>/ dir (never
# rm's a shared dir) and copies the resulting .ply into outputs/models/.
#
# Usage: recon_run.sh [video] [iters] [nframes] [label]
#   video   : input clip            (default in/IMG_8057.mp4)
#   iters   : Brush training steps  (default 7000; ~2000 = quick smoke test, 30000 = quality)
#   nframes : frames to extract     (default 80)
#   label   : run name              (default = timestamp; sets the output folder/ply names)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VIDEO="${1:-$ROOT/in/IMG_8057.mp4}"
ITERS="${2:-7000}"
NFRAMES="${3:-80}"
LABEL="${4:-$(date +%Y%m%d_%H%M%S)}"
BRUSH="$ROOT/brush/target/release/brush"
WORK="$ROOT/recon/runs/$LABEL"
IMAGES="$WORK/images"

[ -x "$BRUSH" ] || { echo "brush binary not found at $BRUSH"; exit 1; }
[ -f "$VIDEO" ] || { echo "video not found: $VIDEO"; exit 1; }
[ -e "$WORK" ] && { echo "run dir already exists, refusing to overwrite: $WORK"; exit 1; }
mkdir -p "$IMAGES" "$ROOT/outputs/models"

echo "== [1/3] extract $NFRAMES frames from $(basename "$VIDEO") =="
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$VIDEO")
FPS=$(python3 -c "print(max($NFRAMES/$DUR, 0.1))")
ffmpeg -y -loglevel error -i "$VIDEO" \
  -vf "fps=$FPS,scale=1280:1280:force_original_aspect_ratio=decrease" \
  -frames:v "$NFRAMES" "$IMAGES/%04d.jpg"
echo "   extracted $(ls "$IMAGES" | wc -l | tr -d ' ') frames"

echo "== [2/3] SfM via pycolmap (camera poses) =="
# NOTE: the Homebrew COLMAP binary's feature matcher SIGBUS-crashes on Apple
# Silicon, so we drive SfM through the pycolmap wheel instead (see recon_sfm.py).
"$ROOT/.venv/bin/python" "$ROOT/recon_sfm.py" "$IMAGES" "$WORK"
[ -d "$WORK/sparse/0" ] || { echo "   SfM produced NO model (poses failed)"; exit 2; }

echo "== [3/3] Brush Gaussian Splatting ($ITERS iters, Metal GPU) =="
"$BRUSH" "$WORK" \
  --total-train-iters "$ITERS" \
  --export-every "$ITERS" \
  --export-path "$WORK/out" \
  --export-name "head_{iter}.ply" \
  --max-resolution 1280

# Preserve the model(s) under outputs/ with the run label (never overwrites).
for p in "$WORK"/out/head_*.ply; do
  [ -e "$p" ] && cp "$p" "$ROOT/outputs/models/${LABEL}_$(basename "$p")"
done
echo "== done =="
echo "   run dir : $WORK"
echo "   models  : $ROOT/outputs/models/${LABEL}_head_*.ply"
