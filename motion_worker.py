"""Real motion-video worker adapter.

The main AutoPoster app can call a separate GPU worker over HTTP. For a local
GPU worker, set MOTION_WORKER_URL to its /generate endpoint. The worker is
kept separate because ordinary Codespaces do not guarantee an NVIDIA GPU.
"""
from __future__ import annotations
import os, requests
from pathlib import Path


def generate_motion_clip(prompt: str, output: str, width: int = 832, height: int = 480, seconds: int = 5) -> str:
    url=os.getenv("MOTION_WORKER_URL")
    if not url:
        raise RuntimeError("MOTION_WORKER_URL is not configured. Start the GPU motion worker and set its URL.")
    r=requests.post(url.rstrip("/")+"/generate",json={"prompt":prompt,"width":width,"height":height,"seconds":seconds},timeout=900)
    r.raise_for_status()
    data=r.json()
    source=data.get("video_path") or data.get("url")
    if not source: raise RuntimeError("Motion worker returned no video_path/url")
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    if source.startswith("http"):
        blob=requests.get(source,timeout=900); blob.raise_for_status(); out.write_bytes(blob.content)
    else:
        out.write_bytes(Path(source).read_bytes())
    return str(out)
