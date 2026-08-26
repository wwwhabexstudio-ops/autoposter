"""Local media helpers: branding, subtitles and optional background audio mixing."""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path


def _ffmpeg():
    exe=shutil.which("ffmpeg")
    if not exe: raise RuntimeError("FFmpeg is required")
    return exe


def burn_logo(input_video: str, logo: str, output: str, position: str="top-right", opacity: float=0.8) -> str:
    pos={"top-right":"W-w-24:24", "top-left":"24:24", "bottom-right":"W-w-24:H-h-24", "bottom-left":"24:H-h-24"}.get(position,"W-w-24:24")
    # Keep logo readable while allowing a simple opacity control.
    filter_complex=f"[1:v]format=rgba,colorchannelmixer=aa={max(0,min(1,opacity))}[logo];[0:v][logo]overlay={pos}"
    cmd=[_ffmpeg(),"-y","-i",input_video,"-i",logo,"-filter_complex",filter_complex,"-c:a","copy",output]
    subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return output


def write_srt(lines: list[tuple[float,float,str]], output: str) -> str:
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    def ts(x):
        ms=int(round(x*1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    with out.open("w",encoding="utf-8") as f:
        for i,(a,b,t) in enumerate(lines,1): f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n")
    return str(out)


def mix_background_music(video: str, music: str, output: str, music_volume: float=0.12) -> str:
    cmd=[_ffmpeg(),"-y","-i",video,"-stream_loop","-1","-i",music,"-filter_complex",f"[1:a]volume={music_volume}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]","-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-shortest",output]
    subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return output
