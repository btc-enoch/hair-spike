#!/usr/bin/env python3
"""
Spike 1 pre-flight: is the capture good enough to reconstruct a 3D head from?
Reconstruction (COLMAP/Gaussian Splatting) fails on motion blur and poor angular
coverage — independent of which tool runs it. So before spending GPU money:
  1. extract frames,
  2. score each for sharpness (variance of Laplacian — low = motion blur),
  3. curate the sharpest frame per evenly-spaced time bin (keeps rotation coverage),
  4. flag blur risk.
Output: recon/keep/ — a clean frame set ready for COLMAP / a GS pipeline.
"""
import subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
RAW, KEEP = ROOT/"recon"/"raw", ROOT/"recon"/"keep"


def sh(*c):
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    return r.stdout


def lap_var(path):
    g = np.asarray(Image.open(path).convert("L"), dtype=np.float64)
    lap = (4*g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1]
           - g[1:-1, :-2] - g[1:-1, 2:])      # discrete Laplacian
    return float(lap.var())


def main():
    video = sys.argv[1] if len(sys.argv) > 1 else "in/IMG_8052.mp4"
    n_raw, n_keep = 48, 16
    for d in (RAW, KEEP):
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*.png"):
            f.unlink()
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=nw=1:nk=1", video).strip())
    sh("ffmpeg", "-y", "-i", video, "-frames:v", str(n_raw), "-vf",
       f"fps={n_raw/dur},scale=720:720:force_original_aspect_ratio=decrease",
       str(RAW/"raw_%03d.png"))
    frames = sorted(RAW.glob("raw_*.png"))
    sharp = [(f, lap_var(f)) for f in frames]
    vals = np.array([s for _, s in sharp])
    print(f"clip {dur:.1f}s | {len(frames)} frames | sharpness(varLap) "
          f"min {vals.min():.0f}  median {np.median(vals):.0f}  max {vals.max():.0f}")

    # curate: sharpest frame in each of n_keep evenly-spaced bins (keeps coverage)
    kept = []
    for i, b in enumerate(np.array_split(range(len(sharp)), n_keep), 1):
        if len(b) == 0:
            continue
        best = max((sharp[j] for j in b), key=lambda x: x[1])
        kept.append(best[1])
        Image.open(best[0]).save(KEEP/f"keep_{i:02d}.png")
    thr = np.median(vals) * 0.4
    print(f"curated {len(kept)} sharp, evenly-spaced frames -> recon/keep/")
    print(f"blur risk: {(vals < thr).sum()}/{len(vals)} frames below 0.4x median sharpness")
    print("kept-frame sharpness:", " ".join(f"{v:.0f}" for v in kept))


if __name__ == "__main__":
    main()
