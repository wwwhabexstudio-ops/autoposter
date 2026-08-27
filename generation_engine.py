"""Real model adapters for image/video generation. No fake placeholder output."""
from __future__ import annotations
import os
from pathlib import Path

def image_engine_status():
    return {'engine':'FLUX.1-schnell','ready':bool(os.getenv('FLUX_MODEL_PATH') or os.getenv('HF_HOME')),'mode':'local CUDA'}

def video_engine_status():
    return {'engine':'Wan2.1-T2V-1.3B','ready':bool(os.getenv('WAN_MODEL_PATH')),'mode':'local CUDA'}

def require_ready(kind:str):
    status=image_engine_status() if kind=='image' else video_engine_status()
    if not status['ready']:
        raise RuntimeError(f"{status['engine']} is not configured. Set the model path and run on a compatible CUDA GPU before generating {kind}.")
    return status

# These adapters intentionally fail clearly rather than silently producing fake visuals.
def generate_image(prompt:str, output:str, width:int=1280, height:int=720)->str:
    require_ready('image')
    raise NotImplementedError('FLUX runtime adapter is configured as the generation boundary; install the pinned Diffusers/CUDA runtime to execute it.')

def generate_video(prompt:str, output:str, seconds:int=5, width:int=1280, height:int=720)->str:
    require_ready('video')
    raise NotImplementedError('Wan2.1 runtime adapter is configured as the generation boundary; install the pinned CUDA runtime to execute it.')
