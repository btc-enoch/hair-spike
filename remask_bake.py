#!/usr/bin/env python3
"""Re-bake with HAIR-REGION MASKING, reusing EXISTING full-frame edits (no new
BFL spend).

For each view: segment the hair in the already-edited frame, then composite that
generated HAIR onto the ORIGINAL sharp frame (face/neck/background kept pristine).
Train Brush on the composites + render a turntable. The face/background should
come back to base sharpness; only the hair region carries the generated content.

usage: remask_bake.py <orig_dataset> <edited_dir> <label> [--iters N]
  <orig_dataset> : dir with images/ + sparse/0/ (the bald reconstruction)
  <edited_dir>   : dir of already-edited frames (same filenames as originals)
"""
import argparse, shutil, subprocess
from pathlib import Path
import numpy as np
import torch
from PIL import Image, ImageFilter
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

ROOT = Path(__file__).resolve().parent
BRUSH = ROOT / "brush" / "target" / "release" / "brush"
HAIR = 13  # jonathandinu/face-parsing 'hair' class
DEVICE = ("cuda" if torch.cuda.is_available()
          else "mps" if torch.backends.mps.is_available() else "cpu")


def hair_mask(img, proc, seg):
    inp = proc(images=img, return_tensors="pt").to(DEVICE)
    with torch.no_grad():
        logits = seg(**inp).logits
    up = torch.nn.functional.interpolate(logits, size=img.size[::-1],
                                         mode="bilinear", align_corners=False)
    labels = up.argmax(1)[0].byte().cpu().numpy()
    m = ((labels == HAIR) * 255).astype("uint8")
    # dilate a touch + feather so the hairline blends into the original scalp
    return Image.fromarray(m).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("orig")
    ap.add_argument("edited")
    ap.add_argument("label")
    ap.add_argument("--iters", type=int, default=7000)
    a = ap.parse_args()

    origimg = Path(a.orig) / "images"
    sparse = Path(a.orig) / "sparse"
    edited = Path(a.edited)
    bake = ROOT / "recon" / "runs" / f"bake_{a.label}"
    (bake / "images").mkdir(parents=True, exist_ok=True)
    if not (bake / "sparse" / "0").exists():
        shutil.copytree(sparse, bake / "sparse")

    proc = SegformerImageProcessor.from_pretrained("jonathandinu/face-parsing")
    seg = SegformerForSemanticSegmentation.from_pretrained("jonathandinu/face-parsing").to(DEVICE)

    edits = sorted(p for p in edited.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    print(f"[1/3] masking + compositing {len(edits)} views (hair only; no BFL spend)")
    for i, ep in enumerate(edits, 1):
        cand = list(origimg.glob(ep.stem + ".*"))
        if not cand:
            print(f"  skip {ep.name} (no original)"); continue
        original = Image.open(cand[0]).convert("RGB")
        ed = Image.open(ep).convert("RGB").resize(original.size, Image.LANCZOS)
        mask = hair_mask(ed, proc, seg)
        comp = Image.composite(ed, original, mask)  # hair from edit, everything else original
        comp.save(bake / "images" / cand[0].name)
        if i % 10 == 0:
            print(f"  {i}/{len(edits)}")

    print(f"[2/3] training Brush {a.iters} iters on masked composites")
    subprocess.run([str(BRUSH), str(bake), "--total-train-iters", str(a.iters),
                    "--export-every", str(a.iters), "--export-path", str(bake / "out"),
                    "--export-name", "baked_{iter}.ply", "--max-resolution", "1280"], check=True)

    ply = bake / "out" / f"baked_{a.iters}.ply"
    print("[3/3] rendering turntable")
    subprocess.run([str(ROOT / "make_turntable.sh"), str(ply), f"bake_{a.label}",
                    "120", "1.5", "0.1", "0.7", "720", "180", "140", "0.06", "0.35", "2.5"], check=True)
    print(f"done -> outputs/videos/bake_{a.label}_*.mp4")


if __name__ == "__main__":
    main()
