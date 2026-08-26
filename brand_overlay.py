"""Brand logo overlay using FFmpeg."""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path

def add_logo(video:str, logo:str, output:str, position:str='top-right', opacity:float=0.8)->str:
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    coords={'top-right':'W-w-24:24','top-left':'24:24','bottom-right':'W-w-24:H-h-24','bottom-left':'24:H-h-24'}
    xy=coords.get(position,coords['top-right'])
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    filt=f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[logo];[0:v][logo]overlay={xy}"
    subprocess.run([ffmpeg,'-y','-i',video,'-i',logo,'-filter_complex',filt,'-c:a','copy',str(out)],check=True)
    return str(out)
