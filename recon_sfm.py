#!/usr/bin/env python3
"""SfM (camera poses) via pycolmap — replaces the crashing brew COLMAP matcher.
extract features -> match -> incremental mapping -> write COLMAP sparse model.
Usage: recon_sfm.py <images_dir> <out_dir>   (out gets database.db + sparse/0/)
"""
import sys, shutil
from pathlib import Path
import pycolmap

images = Path(sys.argv[1] if len(sys.argv) > 1 else "recon/run/images")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "recon/run")
db = out / "database.db"
sparse = out / "sparse"
sparse.mkdir(parents=True, exist_ok=True)
if db.exists():
    db.unlink()

n = len(list(images.glob("*.jpg"))) + len(list(images.glob("*.png")))
print(f"[sfm] {n} images in {images}")
print("[sfm] extract_features ...")
pycolmap.extract_features(db, images)
print("[sfm] match_exhaustive ...")          # the step that SIGBUS'd in brew colmap
pycolmap.match_exhaustive(db)
print("[sfm] incremental_mapping ...")
maps = pycolmap.incremental_mapping(db, images, sparse)
if not maps:
    print("[sfm] FAILED: no model reconstructed (poses not solved)")
    sys.exit(2)
rec = maps[0]
print(f"[sfm] OK: registered {rec.num_reg_images()}/{n} images, "
      f"{rec.num_points3D()} 3D points")
# write to sparse/0 in COLMAP format for Brush
m0 = sparse / "0"
m0.mkdir(exist_ok=True)
rec.write(m0)
print(f"[sfm] wrote model -> {m0}")
