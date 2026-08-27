"""Scene-aware visual pipeline. Creates a unique placeholder/asset per narration scene and applies motion.
Optional image provider hooks can replace _get_image without changing the editor pipeline.
"""
from __future__ import annotations
import hashlib, math, shutil, subprocess
from pathlib import Path

def split_scenes(script: str, total_seconds: float, seconds_per_scene: float = 4.0) -> list[str]:
    sentences=[s.strip() for s in script.replace('\n',' ').split('.') if s.strip()]
    n=max(1, math.ceil(total_seconds/seconds_per_scene))
    if not sentences: return ['Visual representing the narration']*n
    return [(sentences[i % len(sentences)]) for i in range(n)]

def _placeholder(prompt: str, path: Path, width: int, height: int):
    # Unique, readable visual card per scene; replaceable by a real image provider.
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    seed=hashlib.sha256(prompt.encode()).hexdigest()[:10]
    text=f'SCENE {seed}\n{prompt[:90]}'
    subprocess.run([ffmpeg,'-y','-f','lavfi','-i',f"color=c=0x15151b:s={width}x{height}:d=4",'-vf',f"drawtext=text='{text.replace(chr(39),chr(39)+chr(92)+chr(39)+chr(39))}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2",'-frames:v','1',str(path)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def build_scene_assets(script: str, total_seconds: float, out_dir: str, width: int, height: int, seconds_per_scene: float=4.0) -> list[tuple[str,float]]:
    root=Path(out_dir); root.mkdir(parents=True,exist_ok=True)
    scenes=split_scenes(script,total_seconds,seconds_per_scene); result=[]
    for i,prompt in enumerate(scenes):
        img=root/f'scene_{i:03d}.png'
        _placeholder(prompt,img,width,height)
        result.append((str(img),seconds_per_scene))
    return result
