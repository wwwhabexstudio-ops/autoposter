"""Free-first AI image scene generation and 3-5 second motion assembly.
Uses Pollinations' public image endpoint when available; no API key is required.
A local image can be supplied as fallback. External services may impose limits.
"""
from __future__ import annotations
import re, shutil, subprocess, urllib.parse
from pathlib import Path
import requests

def _safe(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]+','_',s)[:70].strip('_') or 'scene'

def generate_image(prompt: str, output: str, width: int = 1280, height: int = 720) -> str:
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    encoded=urllib.parse.quote(prompt, safe='')
    url=f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"
    r=requests.get(url,timeout=120); r.raise_for_status(); out.write_bytes(r.content)
    return str(out)

def image_to_motion(image: str, output: str, width: int, height: int, seconds: float = 4.0, direction: int = 1) -> str:
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    frames=max(2,int(seconds*30)); out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    zoom='min(zoom+0.0015,1.12)' if direction>0 else 'max(zoom-0.0015,1.0)'
    vf=f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=30,format=yuv420p"
    subprocess.run([ffmpeg,'-y','-loop','1','-i',image,'-vf',vf,'-t',str(seconds),'-an','-c:v','libx264','-pix_fmt','yuv420p',str(out)],check=True)
    return str(out)

def make_scene_clips(scenes:list[dict], asset_dir:str, clip_dir:str, width:int, height:int, seconds_default:float=4.0)->list[str]:
    assets=Path(asset_dir); clips=Path(clip_dir); assets.mkdir(parents=True,exist_ok=True); clips.mkdir(parents=True,exist_ok=True)
    result=[]
    for idx,scene in enumerate(scenes):
        prompt=scene.get('visual_prompt','cinematic documentary scene')
        img=assets/f"scene_{idx+1:03d}_{_safe(prompt)}.jpg"
        if not img.exists(): generate_image(prompt,str(img),width,height)
        seconds=float(scene.get('duration_seconds') or seconds_default); seconds=max(3,min(5,seconds))
        clip=clips/f"scene_{idx+1:03d}.mp4"; image_to_motion(str(img),str(clip),width,height,seconds,1 if idx%2==0 else -1); result.append(str(clip))
    return result

def concat_clips(clips:list[str], output:str)->str:
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True); listing=out.with_suffix('.txt')
    listing.write_text('\n'.join("file '"+str(Path(c).resolve()).replace("'","'\\''")+"'" for c in clips),encoding='utf-8')
    subprocess.run([ffmpeg,'-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(out)],check=True)
    return str(out)
