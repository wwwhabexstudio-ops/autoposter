"""Real open-model image/video generation.

Imports are lazy so the normal CPU Codespace can still run the UI. Actual
inference requires a CUDA worker with the model dependencies installed.
"""
from __future__ import annotations
import os
from pathlib import Path


def _cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def image_engine_status():
    return {"engine": os.getenv("IMAGE_MODEL", "FLUX.1-schnell"), "ready": _cuda(), "cuda": _cuda(), "mode": "CUDA"}


def video_engine_status():
    return {"engine": os.getenv("VIDEO_MODEL", "Wan2.1-T2V-1.3B-Diffusers"), "ready": _cuda(), "cuda": _cuda(), "mode": "CUDA"}


def require_ready(kind: str):
    status = image_engine_status() if kind == "image" else video_engine_status()
    if not status["cuda"]:
        raise RuntimeError("Real AI generation requires a CUDA GPU worker. The Codespace CPU cannot run FLUX/Wan efficiently.")
    return status


def generate_image(prompt: str, output: str, width: int = 1280, height: int = 720, steps: int = 4) -> str:
    require_ready("image")
    import torch
    from diffusers import FluxPipeline
    model = os.getenv("FLUX_MODEL_PATH", "black-forest-labs/FLUX.1-schnell")
    pipe = FluxPipeline.from_pretrained(model, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    image = pipe(prompt, height=height, width=width, guidance_scale=0.0,
                 num_inference_steps=steps, max_sequence_length=256).images[0]
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return str(out)


def generate_video(prompt: str, output: str, seconds: int = 5, width: int = 832, height: int = 480, steps: int = 20) -> str:
    require_ready("video")
    import torch
    from diffusers import WanPipeline
    from diffusers.utils import export_to_video
    model = os.getenv("WAN_MODEL_PATH", "Wan-AI/Wan2.1-T2V-1.3B-Diffusers")
    pipe = WanPipeline.from_pretrained(model, torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    fps = 16
    frames = max(1, int(seconds * fps))
    result = pipe(prompt=prompt, num_frames=frames, height=height, width=width,
                   num_inference_steps=steps).frames[0]
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(result, str(out), fps=fps)
    return str(out)
