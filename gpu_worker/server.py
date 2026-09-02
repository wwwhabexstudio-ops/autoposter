"""FastAPI worker for the real Wan2.1 T2V 1.3B model."""
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
app=FastAPI(title="AutoPoster Wan2.1 Motion Worker")
pipe=None

class Job(BaseModel):
    prompt:str
    width:int=832
    height:int=480
    seconds:int=4

@app.on_event("startup")
def load():
    global pipe
    if not torch.cuda.is_available(): raise RuntimeError("CUDA GPU required for Wan2.1 motion worker")
    vae=AutoencoderKLWan.from_pretrained(MODEL,subfolder="vae",torch_dtype=torch.float32)
    pipe=WanPipeline.from_pretrained(MODEL,vae=vae,torch_dtype=torch.bfloat16)
    pipe.to("cuda")

@app.get("/health")
def health():
    return {"ok":pipe is not None,"cuda":torch.cuda.is_available(),"model":MODEL}

@app.post("/generate")
def generate(job:Job):
    if pipe is None: raise HTTPException(503,"Wan2.1 worker is not ready")
    # Wan T2V expects a 4n+1 frame count. Keep clips around the requested 3-5 seconds.
    requested=max(3,min(5,job.seconds)); raw=max(1,round(requested*15)); frames=max(13,4*((raw-1)//4)+1)
    # Keep generation dimensions within the model's practical 480p-class range.
    width=max(256,min(832,int(job.width))); height=max(256,min(832,int(job.height)))
    width=width-(width%16); height=height-(height%16)
    try:
        result=pipe(prompt=job.prompt,negative_prompt="static image, still frame, blurry, low quality, distorted, text, watermark",
                    height=height,width=width,num_frames=frames,guidance_scale=5.0)
        path=Path(tempfile.gettempdir())/f"autoposter_{os.getpid()}_{abs(hash(job.prompt))}.mp4"
        export_to_video(result.frames[0],str(path),fps=15)
        return {"video_path":str(path),"seconds":frames/15,"frames":frames,"model":MODEL}
    except Exception as e:
        raise HTTPException(500,str(e))

@app.get("/video/{name}")
def video(name:str):
    path=Path(tempfile.gettempdir())/name
    if not path.exists(): raise HTTPException(404)
    return FileResponse(path,media_type="video/mp4")
