#!/usr/bin/env python3
"""Single-round 3D hair BAKE test.

Tests the core bet of the iterative-bake approach in ONE round:
  edit every dataset view with BFL ("add hair") -> train Brush on the edited
  views (using the ORIGINAL poses) -> render a turntable.
Question: does training one 3D model on inconsistent per-view hair edits AVERAGE
them into a CONSISTENT 3D hairstyle, or a blurry mess?

usage: bake.py <dataset_dir> "<style>" <label> [--iters N]
  <dataset_dir> must contain images/ + sparse/0/  (produced by recon_run.sh)
Needs BFL_API_KEY. Non-destructive: writes recon/runs/bake_<label>/ + outputs/.
"""
import argparse, base64, io, os, shutil, subprocess, sys, time
from pathlib import Path
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
BRUSH = ROOT / "brush" / "target" / "release" / "brush"
PROMPT = ("Add a full head of {style} to this person. Keep the exact same face, "
          "identity, skin, expression, lighting, background and camera angle. "
          "Photorealistic.")


def _retry(fn, tries=5):
    """Run a network call with retries + backoff so a transient timeout/blip
    doesn't kill the whole bake."""
    for k in range(tries):
        try:
            return fn()
        except requests.exceptions.RequestException as e:
            if k == tries - 1:
                raise
            print(f"    net hiccup ({type(e).__name__}), retry {k+1}/{tries-1} ...")
            time.sleep(3 * (k + 1))


def bfl_edit(img, style, key, model="flux-kontext-pro"):
    buf = io.BytesIO(); img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    hdr = {"x-key": key, "Content-Type": "application/json", "accept": "application/json"}
    r = _retry(lambda: requests.post(f"https://api.bfl.ai/v1/{model}", timeout=120, headers=hdr,
                                     json={"prompt": PROMPT.format(style=style), "input_image": b64,
                                           "output_format": "png"}))
    if r.status_code >= 300:
        sys.exit(f"BFL submit {r.status_code}: {r.text[:200]}")
    d = r.json()
    poll = d.get("polling_url") or f"https://api.bfl.ai/v1/get_result?id={d['id']}"
    for _ in range(240):
        time.sleep(1.0)
        j = _retry(lambda: requests.get(poll, headers=hdr, timeout=120)).json()
        st = j.get("status")
        if st == "Ready":
            data = _retry(lambda: requests.get(j["result"]["sample"], timeout=120)).content
            return Image.open(io.BytesIO(data))
        if st and st not in ("Pending", "Processing", "Queued"):
            sys.exit(f"BFL job failed: {j}")
    sys.exit("BFL timed out")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("style")
    ap.add_argument("label")
    ap.add_argument("--iters", type=int, default=7000)
    a = ap.parse_args()
    key = os.environ.get("BFL_API_KEY") or sys.exit("set BFL_API_KEY")

    src = Path(a.dataset)
    srcimg, srcsparse = src / "images", src / "sparse"
    if not (srcimg.exists() and (srcsparse / "0").exists()):
        sys.exit(f"{src} needs images/ + sparse/0/ (run recon_run.sh first)")

    bake = ROOT / "recon" / "runs" / f"bake_{a.label}"
    (bake / "images").mkdir(parents=True, exist_ok=True)   # resumable: ok if exists
    if not (bake / "sparse" / "0").exists():
        shutil.copytree(srcsparse, bake / "sparse")        # reuse original poses (once)

    imgs = sorted(p for p in srcimg.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    todo = [p for p in imgs if not (bake / "images" / p.name).exists()]  # skip done
    done = len(imgs) - len(todo)
    print(f"[1/3] editing views via BFL -> '{a.style}'  ({done} already done, {len(todo)} to do)")
    for i, p in enumerate(todo, 1):
        t = time.time()
        ed = bfl_edit(Image.open(p).convert("RGB"), a.style, key)
        ed.convert("RGB").save(bake / "images" / p.name)   # same filename -> poses match
        print(f"  {i}/{len(todo)} {p.name}  {time.time()-t:.1f}s")

    print(f"[2/3] training Brush {a.iters} iters on edited views")
    subprocess.run([str(BRUSH), str(bake), "--total-train-iters", str(a.iters),
                    "--export-every", str(a.iters), "--export-path", str(bake / "out"),
                    "--export-name", "baked_{iter}.ply", "--max-resolution", "1280"], check=True)

    ply = bake / "out" / f"baked_{a.iters}.ply"
    print(f"[3/3] rendering turntable from {ply.name}")
    subprocess.run([str(ROOT / "make_turntable.sh"), str(ply), f"bake_{a.label}",
                    "120", "1.5", "0.1", "0.7", "720", "180", "140", "0.06", "0.35", "2.5"],
                   check=True)
    print(f"\nbaked model: {ply}\nturntable saved under outputs/videos/bake_{a.label}_*.mp4")


if __name__ == "__main__":
    main()
