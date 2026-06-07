# Lightweight orchestration container: frame-split + API calls + reassembly.
# The generative model runs in Replicate's cloud, NOT here, so this image
# stays small and needs no GPU (which Docker on macOS can't provide anyway).
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir requests
COPY hairswap.py .

# Args after the image name (e.g. --video ... --style ...) flow to the script.
ENTRYPOINT ["python3", "hairswap.py"]
