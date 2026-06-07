#!/usr/bin/env bash
# Render a turntable mp4 from a splat .ply into outputs/, NEVER overwriting:
# every run gets a unique timestamped frames dir + mp4 under outputs/.
#
# usage: make_turntable.sh <ply> [label] [frames] [dist_mult] [elev] [fov] [size] \
#                          [az_center] [az_sweep] [opac_thr] [scale_mult] [keep_mult]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PLY="${1:?need a .ply path}"
LABEL="${2:-turntable}"
FRAMES="${3:-120}"; DM="${4:-1.5}"; ELEV="${5:-0.1}"; FOV="${6:-0.7}"; SIZE="${7:-720}"
AZC="${8:-180}"; AZS="${9:-140}"; OPAC="${10:-0.06}"; SCM="${11:-0.35}"; KPM="${12:-2.5}"

[ -f "$PLY" ] || { echo "ply not found: $PLY"; exit 1; }
TS="$(date +%Y%m%d_%H%M%S)"
FRAMEDIR="$ROOT/outputs/frames/${LABEL}_${TS}"
MP4="$ROOT/outputs/videos/${LABEL}_${TS}.mp4"
mkdir -p "$FRAMEDIR" "$ROOT/outputs/videos"

"$ROOT/brush/target/release/brush-orbit" "$PLY" "$FRAMEDIR" \
  "$FRAMES" "$DM" "$ELEV" "$FOV" "$SIZE" "$AZC" "$AZS" "$OPAC" "$SCM" "$KPM"

export PATH="/opt/homebrew/bin:$PATH"
ffmpeg -y -loglevel error -framerate 30 -i "$FRAMEDIR/frame_%04d.png" \
  -c:v libx264 -pix_fmt yuv420p "$MP4"

echo "saved video : $MP4"
echo "saved frames: $FRAMEDIR"
