"""AutoPoster free GPU worker using Wan2.1 1.3B.
Run on a CUDA machine such as the user's free Google Colab T4.
"""
from __future__ import annotations
import os, secrets, uuid
from pathlib import Path
import torch
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from diffusers import WanPipeline
from diffusers.schedulers.scheduling_unipc_multistep import UniPCMultistepScheduler
from diffusers.utils import export_to_video

OUT=Path(os.getenv("GPU_WORKER_OUTPUT","/content/autoposter_outputs")); OUT.mkdir(parents=True,exist_ok=True)
TOKEN=os.getenv("GPU_WORKER_TOKEN","")
MODEL_ID=os.getenv("WAN_MODEL_ID","Wan-AI/Wan2.1-T2V-1.3B-Diffusers")
app=FastAPI(title="AutoPoster GPU Worker",version="0.1.0")
_pipe=None
class GenerateRequest(BaseModel):
    prompt:str=Field(min_length=10,max_length=4000)
    negative_prompt:str="blurry, low quality, distorted face, deformed hands, text, subtitles, watermark"
    seconds:int=Field(default=5,ge=3,le=8)
    width:int=Field(default=832,ge=256,le=1280)
    height:int=Field(default=480,ge=256,le=720)
    steps:int=Field(default=20,ge=8,le=40)
    seed:int|None=None

def auth(token):
    return not TOKEN or (token is not None and secrets.compare_digest(token,TOKEN))

def pipeline():
    global _pipe
    if _pipe is None:
        if not torch.cuda.is_available(): raise RuntimeError("CUDA GPU is required")
        _pipe=WanPipeline.from_pretrained(MODEL_ID,torch_dtype=torch.float16)
        _pipe.scheduler=UniPCMultistepScheduler.from_config(_pipe.scheduler.config,flow_shift=3.0)
        _pipe.enable_model_cpu_offload()
    return _pipe

@app.get("/health")
def health():
    return {"ok":True,"cuda":torch.cuda.is_available(),"gpu":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"model":MODEL_ID}

@app.post("/generate")
def generate(req:GenerateRequest,x_autoposter_token:str|None=Header(default=None)):
    if not auth(x_autoposter_token): raise HTTPException(401,"Invalid GPU worker token")
    try:
        p=pipeline(); frames=max(49,min(97,req.seconds*16)); seed=req.seed if req.seed is not None else secrets.randbelow(2**31-1)
        result=p(prompt=req.prompt,negative_prompt=req.negative_prompt,width=req.width,height=req.height,num_frames=frames,num_inference_steps=req.steps,guidance_scale=5.0,generator=torch.Generator(device="cpu").manual_seed(seed))
        job=uuid.uuid4().hex; output=OUT/f"{job}.mp4"; export_to_video(result.frames[0],str(output),fps=16)
        return {"ok":True,"job_id":job,"seconds":req.seconds,"seed":seed,"download_path":f"/download/{job}"}
    except Exception as exc: raise HTTPException(500,str(exc)) from exc

@app.get("/download/{job_id}")
def download(job_id:str,x_autoposter_token:str|None=Header(default=None)):
    if not auth(x_autoposter_token): raise HTTPException(401,"Invalid GPU worker token")
    path=OUT/f"{job_id}.mp4"
    if not path.exists(): raise HTTPException(404,"Video not found")
    return FileResponse(path,media_type="video/mp4",filename=path.name)

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host=os.getenv("GPU_WORKER_HOST","0.0.0.0"),port=int(os.getenv("GPU_WORKER_PORT","7860")))
