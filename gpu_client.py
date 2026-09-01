"""Client for the optional AutoPoster CUDA video worker."""
from __future__ import annotations
import os
from pathlib import Path
import requests

def worker_url() -> str:
    return os.getenv("GPU_WORKER_URL", "").rstrip("/")

def worker_token() -> str:
    return os.getenv("GPU_WORKER_TOKEN", "")

def health() -> dict:
    url=worker_url()
    if not url: raise RuntimeError("GPU_WORKER_URL is not configured")
    r=requests.get(f"{url}/health",timeout=20); r.raise_for_status(); return r.json()

def generate_clip(prompt:str, output:str, seconds:int=5, width:int=832, height:int=480, steps:int=20, seed:int|None=None) -> str:
    url=worker_url()
    if not url: raise RuntimeError("GPU_WORKER_URL is not configured")
    headers={"X-AutoPoster-Token":worker_token()} if worker_token() else {}
    payload={"prompt":prompt,"seconds":seconds,"width":width,"height":height,"steps":steps}
    if seed is not None: payload["seed"]=seed
    r=requests.post(f"{url}/generate",json=payload,headers=headers,timeout=max(300,seconds*120)); r.raise_for_status(); job=r.json()["job_id"]
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    with requests.get(f"{url}/download/{job}",headers=headers,stream=True,timeout=180) as d:
        d.raise_for_status()
        with out.open("wb") as f:
            for chunk in d.iter_content(chunk_size=1024*1024):
                if chunk: f.write(chunk)
    return str(out)
