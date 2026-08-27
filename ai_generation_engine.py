"""Model-agnostic AI image/video generation engine.
Uses local open-weight backends when GPU/model paths are available and fails clearly otherwise.
"""
from __future__ import annotations
import os, subprocess, shutil
from pathlib import Path

def device() -> str:
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except Exception:
        return 'cpu'

def generate_image(prompt: str, output: str, width: int=1024, height: int=576, steps: int=4) -> str:
    """FLUX.1-schnell via diffusers; requires a compatible GPU for practical use."""
    try:
        import torch
        from diffusers import FluxPipeline
    except ImportError as e:
        raise RuntimeError('Install torch and diffusers for the local AI image engine') from e
    if device() != 'cuda': raise RuntimeError('AI image generation needs a CUDA GPU for practical local generation')
    pipe=FluxPipeline.from_pretrained('black-forest-labs/FLUX.1-schnell', torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()
    image=pipe(prompt=prompt,height=height,width=width,num_inference_steps=steps,guidance_scale=0.0).images[0]
    Path(output).parent.mkdir(parents=True,exist_ok=True); image.save(output); return output

def generate_video(prompt: str, output: str, width: int=832, height: int=480, seconds: int=5) -> str:
    """Wan2.1 T2V worker launcher. Set WAN_ROOT to a checkout with Wan2.1 and model weights."""
    root=os.getenv('WAN_ROOT')
    ckpt=os.getenv('WAN_CKPT')
    if not root or not ckpt: raise RuntimeError('Set WAN_ROOT and WAN_CKPT to enable the local Wan2.1 video engine')
    if device() != 'cuda': raise RuntimeError('AI video generation needs a CUDA GPU')
    size=f'{width}*{height}'
    cmd=['python',str(Path(root)/'generate.py'),'--task','t2v-1.3B','--size',size,'--ckpt_dir',ckpt,'--prompt',prompt,'--offload_model','True']
    subprocess.run(cmd,check=True)
    # Wan writes to its configured results directory; callers should pass/relocate the produced mp4.
    return output
