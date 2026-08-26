"""Local-first finished-video factory.
Creates a real MP4 from narration plus a generated visual background using FFmpeg.
Optional visual assets can be supplied per scene later.
"""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path

def _run(cmd: list[str]):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def make_video(audio: str, output: str, width: int, height: int, duration: float | None = None, image: str | None = None) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg: raise RuntimeError("FFmpeg is not installed on the host")
    out=Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    src=image if image and Path(image).exists() else None
    if src:
        cmd=[ffmpeg,"-y","-loop","1","-i",src,"-i",audio,"-vf",f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2","-c:v","libx264","-tune","stillimage","-c:a","aac","-shortest","-pix_fmt","yuv420p",str(out)]
    else:
        cmd=[ffmpeg,"-y","-f","lavfi","-i",f"color=c=black:s={width}x{height}","-i",audio,"-c:v","libx264","-c:a","aac","-shortest","-pix_fmt","yuv420p",str(out)]
    _run(cmd); return str(out)
