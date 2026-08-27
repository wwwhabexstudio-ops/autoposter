"""Caption rendering helpers for FFmpeg."""
from __future__ import annotations
from pathlib import Path
import shutil, subprocess

def burn_captions(video:str, srt:str, output:str, style:str='Bold') -> str:
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    styles={'Bold':'FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2','Minimal':'FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,Outline=1,Alignment=2','Boxed':'FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,BorderStyle=4,Alignment=2','Karaoke':'FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2'}
    st=styles.get(style,styles['Bold']); out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    # subtitles filter path needs escaping for FFmpeg on Unix.
    sub=str(Path(srt).resolve()).replace('\\','/').replace(':','\\:')
    vf=f"subtitles='{sub}':force_style='{st}'"
    subprocess.run([ffmpeg,'-y','-i',video,'-vf',vf,'-c:a','copy',str(out)],check=True)
    return str(out)
