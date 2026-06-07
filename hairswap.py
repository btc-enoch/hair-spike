#!/usr/bin/env python3
"""
Hair-swap spike: test whether a GENERATIVE per-frame hair edit holds together
across the frames of a short rotate video.

Architecture: the video plumbing (frame split -> edit -> reassemble) is shared.
The MODEL is a pluggable BACKEND, so we can prove the pipeline now with a cheap
local model and swap in a better one later without touching the rest.

Backends:
  local      SD1.5 + LCM-LoRA inpainting, hair masked via face-parsing.
             Runs natively on Apple Silicon (MPS). Fast (~secs/frame), low-q.
  replicate  Hosted instruction image-editor (Flux Kontext). Needs API token.

Usage:
  # local (no API, runs on your M1 Max):
  .venv/bin/python hairswap.py --backend local --video in/clip.mov \\
      --style "short wavy bob with curtain bangs"

  # cloud (better quality):
  export REPLICATE_API_TOKEN=...
  .venv/bin/python hairswap.py --backend replicate --video in/clip.mov --style "..."

Output: out/edited.mp4 and out/compare.mp4 (orig | edited).
Judge: does the new hair stay coherent as the head turns, or flicker/morph?
"""
import argparse, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRAMES_DIR = ROOT / "frames"
OUT_DIR = ROOT / "out"


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{r.stderr}")
    return r.stdout


# ---------------------------------------------------------------- frame I/O ---
def extract_frames(video: Path, n: int):
    from shutil import which
    if not which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH. brew install ffmpeg")
    FRAMES_DIR.mkdir(exist_ok=True)
    for f in FRAMES_DIR.glob("*.png"):
        f.unlink()
    dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=nw=1:nk=1", str(video)).strip())
    fps = max(n / dur, 0.1)
    sh("ffmpeg", "-y", "-i", str(video), "-vf", f"fps={fps},scale=512:-2",
       "-frames:v", str(n), str(FRAMES_DIR / "orig_%03d.png"))
    frames = sorted(FRAMES_DIR.glob("orig_*.png"))
    print(f"  extracted {len(frames)} frames ({dur:.1f}s clip)")
    return frames


def reassemble():
    sh("ffmpeg", "-y", "-framerate", "8", "-i", str(FRAMES_DIR / "edit_%03d.png"),
       "-c:v", "libx264", "-pix_fmt", "yuv420p", str(OUT_DIR / "edited.mp4"))
    # Force both sides to a common height before stacking so a size mismatch
    # can never break the side-by-side.
    sh("ffmpeg", "-y", "-framerate", "8", "-i", str(FRAMES_DIR / "orig_%03d.png"),
       "-framerate", "8", "-i", str(FRAMES_DIR / "edit_%03d.png"),
       "-filter_complex",
       "[0:v]scale=-2:720[a];[1:v]scale=-2:720[b];[a][b]hstack",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", str(OUT_DIR / "compare.mp4"))


# ------------------------------------------------------------- backends ------
class LocalBackend:
    """SD1.5 + LCM-LoRA inpainting, hair region masked by a face-parser.
    Heavy deps (torch/diffusers) are imported lazily so the replicate path
    needs none of them."""
    HAIR_CLASS = 13  # jonathandinu/face-parsing label id for 'hair'

    def __init__(self, seed: int, steps: int, mask_mode: str = "hair"):
        self.seed, self.steps, self.mask_mode = seed, steps, mask_mode

    def prepare(self):
        import torch
        from diffusers import StableDiffusionInpaintPipeline, LCMScheduler
        from transformers import (SegformerImageProcessor,
                                  SegformerForSemanticSegmentation)
        self.torch = torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        # float32 on MPS is the most numerically stable (avoids NaN frames);
        # SD1.5 is small enough that 64GB handles it comfortably.
        dt = torch.float32
        print(f"  loading SD1.5-inpaint + LCM-LoRA on {self.device} ...")
        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            "stable-diffusion-v1-5/stable-diffusion-inpainting", torch_dtype=dt,
            safety_checker=None)
        pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
        pipe.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
        pipe.fuse_lora()
        pipe.set_progress_bar_config(disable=True)
        self.pipe = pipe.to(self.device)
        print("  loading face-parser for hair masks ...")
        self.seg_proc = SegformerImageProcessor.from_pretrained(
            "jonathandinu/face-parsing")
        self.seg = SegformerForSemanticSegmentation.from_pretrained(
            "jonathandinu/face-parsing").to(self.device)

    def _parse(self, img):
        """Run the face-parser -> (H,W) array of class ids."""
        inp = self.seg_proc(images=img, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            logits = self.seg(**inp).logits
        up = self.torch.nn.functional.interpolate(
            logits, size=img.size[::-1], mode="bilinear", align_corners=False)
        return up.argmax(1)[0].byte().cpu().numpy()

    @staticmethod
    def _morph(arr_bool, op, size):
        from PIL import Image, ImageFilter
        import numpy as np
        im = Image.fromarray((arr_bool * 255).astype("uint8"))
        f = ImageFilter.MaxFilter(size) if op == "dilate" else ImageFilter.MinFilter(size)
        return np.array(im.filter(f)) > 127

    def _hair_mask(self, img):
        """Existing-hair region — for RESTYLING hair that's already there."""
        from PIL import Image
        labels = self._parse(img)
        m = self._morph(labels == self.HAIR_CLASS, "dilate", 9)
        return Image.fromarray((m * 255).astype("uint8"))

    def _scalp_mask(self, img):
        """'Where hair SHOULD go' — for GROWING hair onto a bald/short head.
        Scalp and face share the 'skin' class, so we can't separate them by class
        — we use GEOMETRY: hair lives ABOVE the brow line (crown/forehead) plus a
        HALO around the upper head (room for length/volume, currently background),
        minus the facial features we must keep visible. This is the input
        canonicalization idea: a bald head becomes a clean canvas to draw onto."""
        from PIL import Image
        import numpy as np
        labels = self._parse(img)
        H, W = labels.shape
        HEAD = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]   # whole head incl scalp
        head = np.isin(labels, HEAD)
        protect = self._morph(np.isin(labels, [2, 4, 5, 6, 7, 10, 11, 12]), "dilate", 7)
        rows = np.arange(H)[:, None]                          # row index per pixel
        eye = np.where(np.isin(labels, [4, 5, 6, 7]))[0]      # eyes+brows rows
        cutoff = int(eye.min()) if eye.size else H // 3       # hairline ~ top of brows
        mouth = np.where(labels == 10)[0]
        low = int(mouth.max()) if mouth.size else (2 * H) // 3
        scalp_top = head & (rows <= cutoff)                  # crown + forehead
        halo = self._morph(head, "dilate", 31) & ~head & (rows <= low)  # framing/volume
        target = self._morph((scalp_top | halo) & ~protect, "dilate", 5)
        return Image.fromarray((target * 255).astype("uint8"))

    def edit(self, img, style):
        from PIL import Image
        # Preserve the frame's aspect ratio. SD1.5 wants dims that are multiples
        # of 8 and works best with the long side ~512-640; run at a work size,
        # then resize the result back to the original frame size so it lines up
        # with the originals (and the side-by-side hstack doesn't break).
        w0, h0 = img.size
        scale = min(640 / max(w0, h0), 1.0)
        wW = max(8, round(w0 * scale / 8) * 8)
        hW = max(8, round(h0 * scale / 8) * 8)
        work = img.resize((wW, hW), Image.LANCZOS)
        mask = (self._scalp_mask(work) if self.mask_mode == "grow"
                else self._hair_mask(work))
        self._n = getattr(self, "_n", 0) + 1
        mask.save(FRAMES_DIR / f"mask_{self._n:03d}.png")  # for inspection
        g = self.torch.Generator(device=self.device).manual_seed(self.seed)
        prompt = f"{style}, photorealistic hair, natural lighting, detailed"
        out = self.pipe(prompt=prompt, image=work, mask_image=mask,
                        width=wW, height=hW, num_inference_steps=self.steps,
                        guidance_scale=1.5, strength=1.0, generator=g).images[0]
        return out.resize((w0, h0), Image.LANCZOS)


class ReplicateBackend:
    def __init__(self, model: str, seed: int):
        self.model, self.seed = model, seed

    def prepare(self):
        import requests, base64, mimetypes
        self.requests, self.base64, self.mimetypes = requests, base64, mimetypes
        self.token = os.environ.get("REPLICATE_API_TOKEN")
        if not self.token:
            sys.exit("Set REPLICATE_API_TOKEN for the replicate backend.")

    def edit(self, img, style):
        import io
        buf = io.BytesIO(); img.save(buf, format="PNG")
        uri = "data:image/png;base64," + self.base64.b64encode(buf.getvalue()).decode()
        prompt = (f"Change only the person's hairstyle to: {style}. Keep the exact "
                  "same face, identity, lighting, background and angle. Photorealistic.")
        r = self.requests.post(
            f"https://api.replicate.com/v1/models/{self.model}/predictions",
            json={"input": {"prompt": prompt, "input_image": uri, "seed": self.seed,
                            "output_format": "png"}}, timeout=180,
            headers={"Authorization": f"Bearer {self.token}", "Prefer": "wait"})
        if r.status_code >= 300:
            sys.exit(f"Replicate error {r.status_code}: {r.text[:300]}")
        out = r.json().get("output")
        url = out[0] if isinstance(out, list) else out
        from PIL import Image; import io as _io
        return Image.open(_io.BytesIO(self.requests.get(url, timeout=120).content))


class BFLBackend:
    """Black Forest Labs native API (first-party Flux Kontext). Submit a job,
    then poll the returned polling_url until the result is Ready."""
    BASE = "https://api.bfl.ai/v1"

    def __init__(self, model: str, seed: int):
        # accept the replicate-style default and normalize to a BFL endpoint name
        self.model = "flux-kontext-pro" if "/" in model else model
        self.seed = seed

    def prepare(self):
        import requests
        self.requests = requests
        self.key = os.environ.get("BFL_API_KEY")
        if not self.key:
            sys.exit("Set BFL_API_KEY for the bfl backend (from your Black Forest "
                     "Labs account → API Keys).")

    def edit(self, img, style):
        import io, base64, time
        buf = io.BytesIO(); img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        prompt = (f"Change only the person's hairstyle to: {style}. Keep the exact "
                  "same face, identity, lighting, background and angle. Photorealistic.")
        hdr = {"x-key": self.key, "Content-Type": "application/json",
               "accept": "application/json"}
        r = self.requests.post(f"{self.BASE}/{self.model}", timeout=60, headers=hdr,
                               json={"prompt": prompt, "input_image": b64,
                                     "seed": self.seed, "output_format": "png"})
        if r.status_code >= 300:
            sys.exit(f"BFL submit error {r.status_code}: {r.text[:300]}")
        data = r.json()
        poll = data.get("polling_url") or f"{self.BASE}/get_result?id={data['id']}"
        for _ in range(180):  # poll up to ~3 min
            time.sleep(1.0)
            j = self.requests.get(poll, headers=hdr, timeout=60).json()
            st = j.get("status")
            if st == "Ready":
                from PIL import Image
                url = j["result"]["sample"]
                return Image.open(io.BytesIO(self.requests.get(url, timeout=120).content))
            if st and st not in ("Pending", "Processing", "Queued"):
                sys.exit(f"BFL job did not succeed: {j}")
        sys.exit("BFL timed out waiting for result")


# ---------------------------------------------------------------- main -------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["local", "replicate", "bfl"], default="local")
    ap.add_argument("--video", required=True)
    ap.add_argument("--style", required=True)
    ap.add_argument("--frames", type=int, default=12)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--steps", type=int, default=6, help="LCM steps (local)")
    ap.add_argument("--mask", choices=["hair", "grow"], default="hair",
                    help="hair=restyle existing hair; grow=add hair onto bald/short head")
    ap.add_argument("--model", default="black-forest-labs/flux-kontext-pro",
                    help="replicate slug, or bfl model name (flux-kontext-pro|flux-kontext-max)")
    a = ap.parse_args()

    video = Path(a.video)
    if not video.exists():
        sys.exit(f"video not found: {video}")
    OUT_DIR.mkdir(exist_ok=True)

    if a.backend == "local":
        backend = LocalBackend(a.seed, a.steps, a.mask)
    elif a.backend == "bfl":
        backend = BFLBackend(a.model, a.seed)
    else:
        backend = ReplicateBackend(a.model, a.seed)

    print(f"[1/4] extracting {a.frames} frames from {video.name}")
    frames = extract_frames(video, a.frames)
    print(f"[2/4] loading backend '{a.backend}'")
    backend.prepare()
    print(f"[3/4] generative hair edit -> '{a.style}'")
    from PIL import Image
    for i, f in enumerate(frames, 1):
        t = time.time()
        out = backend.edit(Image.open(f).convert("RGB"), a.style)
        out.save(FRAMES_DIR / f"edit_{i:03d}.png")
        print(f"  frame {i}/{len(frames)}  {time.time()-t:.1f}s")
    print("[4/4] reassembling videos")
    reassemble()
    print(f"\nDone. Look at:\n  {OUT_DIR/'edited.mp4'}\n  {OUT_DIR/'compare.mp4'} (orig | edited)")
    print("Judge: does the new hair keep the SAME shape/length as the head turns,"
          " or flicker/morph frame to frame?")


if __name__ == "__main__":
    main()
