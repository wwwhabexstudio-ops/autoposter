"""Free/local-first media pipeline.

Uses FFmpeg when installed. Creates simple video slates from text when no
external visual generator is configured, and can mux narration/audio.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    exe = ffmpeg_path()
    if not exe:
        raise RuntimeError("FFmpeg is not installed. Install FFmpeg before rendering videos.")
    return subprocess.run([exe, "-y", *args], capture_output=True, text=True, check=False)


def make_color_clip(output: Path, duration: float, width: int, height: int) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output)
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1500:])
    return output


def mux_audio(video: Path, audio: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run_ffmpeg(["-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-shortest", str(output)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1500:])
    return output
