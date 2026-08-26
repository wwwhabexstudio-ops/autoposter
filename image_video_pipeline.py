"""End-to-end free-first image-scene video pipeline."""
from __future__ import annotations
from pathlib import Path
import shutil, subprocess
from image_scene_factory import make_scene_clips, concat_clips

def render_from_scenes(scenes:list[dict], audio:str, output:str, asset_dir:str, clip_dir:str, width:int, height:int) -> str:
    clips=make_scene_clips(scenes,asset_dir,clip_dir,width,height)
    silent=Path(output).with_name(Path(output).stem+'_visuals.mp4')
    concat_clips(clips,str(silent))
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([ffmpeg,'-y','-i',str(silent),'-i',audio,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-shortest','-movflags','+faststart',str(out)],check=True)
    return str(out)
