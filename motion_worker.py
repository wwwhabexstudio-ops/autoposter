"""Wan2.1 motion-video adapter.

Uses a local CUDA worker when MOTION_WORKER_URL is configured. Otherwise it
connects automatically to the official Wan2.1 Hugging Face Gradio Space.
Supports both text-to-video and image-to-video animation.
"""
from __future__ import annotations
import os, sys, time, subprocess, requests
from pathlib import Path

REMOTE_SPACE = os.getenv("WAN_SPACE_ID", "Wan-AI/Wan2.1")
REMOTE_BASE = "https://wan-ai-wan2-1.hf.space"


def _extract_video_source(value):
    """Find a usable video URL/path inside Gradio's nested return objects."""
    if value is None:
        return None
    if isinstance(value, (str, Path)):
        text = str(value)
        if text.startswith(("http://", "https://", "/", "file://")) or Path(text).exists():
            return text
        return None
    if isinstance(value, dict):
        for key in ("value", "video", "path", "file", "url", "name", "data"):
            if key in value:
                found = _extract_video_source(value[key])
                if found:
                    return found
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _extract_video_source(item)
            if found:
                return found
    return None


def _save_source(source, out: Path) -> str:
    source = _extract_video_source(source) or source
    if isinstance(source, dict):
        source = source.get("url") or source.get("path") or source.get("name")
    if isinstance(source, (list, tuple)) and source:
        return _save_source(source[0], out)
    if not source:
        raise RuntimeError("Wan2.1 returned no video")
    source = str(source)
    out.parent.mkdir(parents=True, exist_ok=True)
    if source.startswith("file://"):
        source = source[7:]
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


def _client():
    try:
        from gradio_client import Client
        return Client
    except Exception:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "gradio-client>=1.7,<2"], check=True)
        from gradio_client import Client
        return Client


def _api_names(client) -> set[str]:
    try:
        info = client.view_api(return_format="dict")
        return set(info.keys()) if isinstance(info, dict) else set()
    except Exception:
        return set()


def _remote_task(client, task_api: str, args: list) -> str:
    result = client.predict(*args, api_name=task_api)
    task_id = result[0] if isinstance(result, (list, tuple)) else result
    if not task_id:
        raise RuntimeError("Wan2.1 remote Space did not return a task id")
    return str(task_id)


def _poll_remote(client, task_id: str, output: str, seconds: int, task_type: str) -> str:
    """Poll using an endpoint exposed by the current official Space."""
    deadline = time.time() + max(720, seconds * 180)
    last_error = None
    api_names = _api_names(client)
    result_api = "/get_result_with_task_id" if "/get_result_with_task_id" in api_names else None
    status_api = "/status_refresh" if "/status_refresh" in api_names else None
    if not result_api and not status_api:
        status_api = "/status_refresh"

    while time.time() < deadline:
        try:
            if result_api:
                status_result = client.predict(task_id, api_name=result_api)
            else:
                # Official Wan2.1 status_refresh(task_id, task, status).
                status_result = client.predict(task_id, task_type, False, api_name=status_api)

            video = _extract_video_source(status_result)
            if video:
                return _save_source(video, Path(output))

            if isinstance(status_result, (list, tuple)) and result_api:
                if status_result and bool(status_result[0]) and len(status_result) > 1 and not status_result[1]:
                    raise RuntimeError("Wan2.1 remote task reported failure")
        except Exception as exc:
            last_error = exc
            if result_api and "Cannot find a function with api_name" in str(exc):
                api_names = _api_names(client)
                result_api = "/get_result_with_task_id" if "/get_result_with_task_id" in api_names else None
                status_api = "/status_refresh" if "/status_refresh" in api_names else status_api
        time.sleep(5)

    detail = f": {last_error}" if last_error else ""
    raise TimeoutError(f"Wan2.1 remote generation timed out{detail}")


def _remote_clip(prompt: str, output: str, width: int, height: int, seconds: int) -> str:
    Client = _client()
    client = Client(REMOTE_SPACE)
    if width == height:
        resolution = "960*960"
    elif width > height:
        resolution = "1280*720"
    else:
        resolution = "720*1280"
    task_id = _remote_task(client, "/t2v_generation_async", [prompt, resolution, True, -1])
    return _poll_remote(client, task_id, output, seconds, "t2v")


def _remote_image_clip(image: str, prompt: str, output: str, seconds: int) -> str:
    Client = _client()
    client = Client(REMOTE_SPACE)
    task_id = _remote_task(client, "/i2v_generation_async", [prompt, image, True, -1])
    return _poll_remote(client, task_id, output, seconds, "i2v")


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
        r = requests.post(local.rstrip("/") + "/generate", json={"prompt":prompt,"width":width,"height":height,"seconds":seconds},timeout=900)
        r.raise_for_status()
        data = r.json()
        source = data.get("video_path") or data.get("url")
        if not source:
            raise RuntimeError("Local Wan2.1 worker returned no video_path/url")
        return _save_source(source, Path(output))
    return _remote_clip(prompt, output, width, height, seconds)


def generate_image_motion_clip(image: str, prompt: str, output: str, width: int = 832, height: int = 480, seconds: int = 5) -> str:
    """Animate a supplied still image with Wan2.1 I2V."""
    image_path = Path(str(image))
    if not image_path.exists():
        raise RuntimeError(f"Input image not found: {image}")
    local = os.getenv("MOTION_WORKER_URL", "").strip()
    if local:
        r = requests.post(
            local.rstrip("/") + "/generate-i2v",
            json={"image_path":str(image_path),"prompt":prompt,"width":width,"height":height,"seconds":seconds},
            timeout=900,
        )
        if r.ok:
            data = r.json()
            source = data.get("video_path") or data.get("url")
            if source:
                return _save_source(source, Path(output))
        raise RuntimeError(f"Local Wan2.1 I2V worker failed: {r.text[:500]}")
    return _remote_image_clip(str(image_path), prompt, output, seconds)
