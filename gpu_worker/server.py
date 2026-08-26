"""FastAPI worker for Wan2.1 T2V 1.3B.
Run this only on a machine with a CUDA GPU and sufficient VRAM.
"""
from __future__ import annotations
import os, tempfile
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import torch
from diffusers import AutoencoderKLWan, WanPipeline
from diffusers.utils import export_to_video

MODEL=os.getenv("WAN_MODEL","Wan-AI/Wan2.1-T2V-1.3B-Diffusers")
app=FastAPI(title="AutoPoster Motion Worker")
pipe=None

class Job(BaseModel):
    prompt:str
    width:int=832
    height:int=480
    seconds:int=5

@app.on_event("startup")
def load():
    global pipe
    if not torch.cuda.is_available(): raise RuntimeError("CUDA GPU required for Wan motion worker")
    vae=AutoencoderKLWan.from_pretrained(MODEL,subfolder="vae",torch_dtype=torch.float32)
    pipe=WanPipeline.from_pretrained(MODEL,vae=vae,torch_dtype=torch.bfloat16)
    pipe.to("cuda")

@app.get("/health")
def health(): return {"ok":True,"cuda":torch.cuda.is_available(),"model":MODEL}

@app.post("/generate")
def generate(job:Job):
    if pipe is None: raise HTTPException(503,"Worker not ready")
    frames=max(17,min(81,job.seconds*15+1))
    try:
        result=pipe(prompt=job.prompt,negative_prompt="static image, blurry, low quality, distorted, text, watermark",height=job.height,width=job.width,num_frames=frames,guidance_scale=5.0)
        path=Path(tempfile.gettempdir())/f"autoposter_{os.getpid()}_{abs(hash(job.prompt))}.mp4"
        export_to_video(result.frames[0],str(path),fps=15)
        return {"video_path":str(path),"seconds":job.seconds}
    except Exception as e:
        raise HTTPException(500,str(e))

@app.get("/video/{name}")
def video(name:str):
    path=Path(tempfile.gettempdir())/name
    if not path.exists(): raise HTTPException(404)
    return FileResponse(path,media_type="video/mp4")
