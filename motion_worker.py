"""Wan2.1 motion-video adapter.

Uses a local CUDA worker when MOTION_WORKER_URL is configured. Otherwise it
connects automatically to the official Wan2.1 Hugging Face Gradio Space.
No static/image video fallback is used.
"""
from __future__ import annotations
import os, time, requests
from pathlib import Path

REMOTE_SPACE = os.getenv("WAN_SPACE_ID", "Wan-AI/Wan2.1")
REMOTE_BASE = "https://wan-ai-wan2-1.hf.space"


def _save_source(source, out: Path) -> str:
    if isinstance(source, dict):
        source = source.get("url") or source.get("path") or source.get("name")
    if isinstance(source, (list, tuple)) and source:
        return _save_source(source[0], out)
    if not source:
        raise RuntimeError("Wan2.1 returned no video")
    source = str(source)
    out.parent.mkdir(parents=True, exist_ok=True)
    if source.startswith("http://") or source.startswith("https://"):
        r = requests.get(source, timeout=900)
        r.raise_for_status()
        out.write_bytes(r.content)
    else:
        src = Path(source)
        if not src.exists():
            raise RuntimeError(f"Wan2.1 returned an unavailable video path: {source}")
        out.write_bytes(src.read_bytes())
    return str(out)


def _remote_clip(prompt: str, output: str, width: int, height: int, seconds: int) -> str:
    try:
        from gradio_client import Client
    except Exception as exc:
        raise RuntimeError("gradio-client is required for automatic Wan2.1 generation") from exc
    client = Client(REMOTE_SPACE, token=os.getenv("HF_TOKEN") or None, verbose=False)
    resolution = f"{width}*{height}"
    result = client.predict(prompt, resolution, True, -1, api_name="/t2v_generation_async")
    task_id = result[0] if isinstance(result, (list, tuple)) else result
    if not task_id:
        raise RuntimeError("Wan2.1 remote Space did not return a task id")
    deadline = time.time() + max(900, seconds * 180)
    while time.time() < deadline:
        try:
            status_result = client.predict(task_id, api_name="/get_result_with_task_id")
            done = False; video = None
            if isinstance(status_result, (list, tuple)):
                done = bool(status_result[0]) if status_result else False
                video = status_result[1] if len(status_result) > 1 else None
            elif isinstance(status_result, dict):
                done = bool(status_result.get("status"))
                video = status_result.get("video_url") or status_result.get("video")
            if done and video:
                return _save_source(video, Path(output))
        except Exception:
            pass
        time.sleep(5)
    raise TimeoutError("Wan2.1 remote generation timed out")


def remote_health() -> tuple[bool, str]:
    try:
        r = requests.get(REMOTE_BASE, timeout=8)
        if r.ok:
            return True, REMOTE_SPACE
    except Exception:
        pass
    return False, REMOTE_SPACE


def wan_available() -> tuple[bool, str]:
    local = os.getenv("MOTION_WORKER_URL", "").strip()
    if local:
        try:
            h = requests.get(local.rstrip("/") + "/health", timeout=8).json()
            if h.get("ok") and h.get("cuda") and "Wan2.1" in str(h.get("model", "")):
                return True, f"local:{h.get('model')}"
            return False, "local Wan2.1 worker is not CUDA-ready"
        except Exception as exc:
            return False, f"local worker unreachable: {exc}"
    return remote_health()


def generate_motion_clip(prompt: str, output: str, width: int = 832, height: int = 480, seconds: int = 5) -> str:
    local = os.getenv("MOTION_WORKER_URL", "").strip()
    if local:
        r = requests.post(local.rstrip("/") + "/generate", json={"prompt": prompt, "width": width, "height": height, "seconds": seconds}, timeout=900)
        r.raise_for_status()
        data = r.json()
        source = data.get("video_path") or data.get("url")
        if not source:
            raise RuntimeError("Local Wan2.1 worker returned no video_path/url")
        return _save_source(source, Path(output))
    return _remote_clip(prompt, output, width, height, seconds)
