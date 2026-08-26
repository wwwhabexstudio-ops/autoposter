"""FFmpeg-based local video rendering utilities."""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path
from video_lab import VideoPlan

def ffmpeg_path() -> str:
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("FFmpeg is not installed on this host")
    return exe

def write_srt(lines: list[tuple[float,float,str]], path: str) -> str:
    def stamp(s: float) -> str:
        ms=int(round((s-int(s))*1000)); total=int(s); h=total//3600; m=(total%3600)//60; sec=total%60
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}" for i,(a,b,text) in enumerate(lines,1)),encoding="utf-8")
    return str(p)

def render_image_sequence(images:list[str],audio:str|None,output:str,plan:VideoPlan)->str:
    if not images: raise ValueError("At least one image is required")
    ff=ffmpeg_path(); out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    concat=out.with_suffix(".concat.txt"); duration=plan.target_duration_seconds/max(1,len(images))
    concat.write_text("\n".join(f"file '{Path(x).resolve()}'\nduration {duration:.3f}" for x in images)+f"\nfile '{Path(images[-1]).resolve()}'\n",encoding="utf-8")
    cmd=[ff,"-y","-f","concat","-safe","0","-i",str(concat)]
    if audio: cmd += ["-i",audio]
    cmd += ["-vf",f"scale={plan.width}:{plan.height}:force_original_aspect_ratio=decrease,pad={plan.width}:{plan.height}:(ow-iw)/2:(oh-ih)/2","-r","30"]
    if audio: cmd += ["-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(out)]
    else: cmd += ["-c:v","libx264","-pix_fmt","yuv420p",str(out)]
    subprocess.run(cmd,check=True); return str(out)
