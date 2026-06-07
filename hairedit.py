#!/usr/bin/env python3
"""Single-image generative hair edit — Spike 2 de-risk test.
Checks the core bet on ONE canonical view before any 3D-bake work:
does a strong instruction model change the hair convincingly AND keep identity?

usage: hairedit.py <image> "<style>" [--backend bfl|replicate] [--model NAME]
Needs BFL_API_KEY (bfl) or REPLICATE_API_TOKEN (replicate).
Outputs a timestamped edit + side-by-side under outputs/hairtest/ (never overwrites).
"""
import argparse, base64, io, os, sys, time
from pathlib import Path
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "hairtest"
PROMPT = ("Change only the person's hairstyle to: {style}. Keep the exact same face, "
          "identity, skin, expression, lighting, background and camera angle. Photorealistic.")


def bfl_edit(img, style, model, key):
    buf = io.BytesIO(); img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    hdr = {"x-key": key, "Content-Type": "application/json", "accept": "application/json"}
    r = requests.post(f"https://api.bfl.ai/v1/{model}", timeout=60, headers=hdr,
                      json={"prompt": PROMPT.format(style=style), "input_image": b64,
                            "output_format": "png"})
    if r.status_code >= 300:
        sys.exit(f"BFL submit error {r.status_code}: {r.text[:300]}")
    d = r.json()
    poll = d.get("polling_url") or f"https://api.bfl.ai/v1/get_result?id={d['id']}"
    for _ in range(180):
        time.sleep(1.0)
        j = requests.get(poll, headers=hdr, timeout=60).json()
        st = j.get("status")
        if st == "Ready":
            url = j["result"]["sample"]
            return Image.open(io.BytesIO(requests.get(url, timeout=120).content))
        if st and st not in ("Pending", "Processing", "Queued"):
            sys.exit(f"BFL job failed: {j}")
    sys.exit("BFL timed out")


def replicate_edit(img, style, model, token):
    buf = io.BytesIO(); img.save(buf, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    r = requests.post(f"https://api.replicate.com/v1/models/{model}/predictions", timeout=180,
                      headers={"Authorization": f"Bearer {token}", "Prefer": "wait"},
                      json={"input": {"prompt": PROMPT.format(style=style), "input_image": uri,
                                      "output_format": "png"}})
    if r.status_code >= 300:
        sys.exit(f"Replicate error {r.status_code}: {r.text[:300]}")
    out = r.json().get("output")
    url = out[0] if isinstance(out, list) else out
    return Image.open(io.BytesIO(requests.get(url, timeout=120).content))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("style")
    ap.add_argument("--backend", choices=["bfl", "replicate"], default="bfl")
    ap.add_argument("--model", default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    img = Image.open(a.image).convert("RGB")
    ts = time.strftime("%Y%m%d_%H%M%S")

    if a.backend == "bfl":
        key = os.environ.get("BFL_API_KEY") or sys.exit("set BFL_API_KEY first")
        edited = bfl_edit(img, a.style, a.model or "flux-kontext-pro", key)
    else:
        tok = os.environ.get("REPLICATE_API_TOKEN") or sys.exit("set REPLICATE_API_TOKEN first")
        edited = replicate_edit(img, a.style, a.model or "black-forest-labs/flux-kontext-pro", tok)

    edp = OUT / f"edit_{ts}.png"
    edited.save(edp)
    e2 = edited.resize((img.width, round(edited.height * img.width / edited.width)))
    cmp = Image.new("RGB", (img.width + e2.width, max(img.height, e2.height)), (255, 255, 255))
    cmp.paste(img, (0, 0)); cmp.paste(e2, (img.width, 0))
    cp = OUT / f"compare_{ts}.png"
    cmp.save(cp)
    print(f"style  : {a.style}")
    print(f"edited : {edp}")
    print(f"compare: {cp}")


if __name__ == "__main__":
    main()
