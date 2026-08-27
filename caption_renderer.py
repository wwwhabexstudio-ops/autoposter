"""Caption rendering helpers for FFmpeg."""
from __future__ import annotations
from pathlib import Path
import shutil, subprocess

def _ts(sec):
    ms=int(sec*1000); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def make_srt(text:str, output:str, seconds_per_chunk:float=3.5) -> str:
    words=text.split(); out=Path(output); out.parent.mkdir(parents=True,exist_ok=True); lines=[]
    for i in range(0,len(words),12):
        chunk=' '.join(words[i:i+12]); start=(i//12)*seconds_per_chunk; end=start+seconds_per_chunk
        lines += [str(i//12+1),f'{_ts(start)} --> {_ts(end)}',chunk,'']
    out.write_text('\n'.join(lines),encoding='utf-8'); return str(out)

def burn_captions(video:str, srt:str, output:str, style:str='Bold') -> str:
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    styles={'Bold':'FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2','Minimal':'FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,Outline=1,Alignment=2','Boxed':'FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,BorderStyle=4,Alignment=2','Karaoke':'FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Alignment=2'}
    st=styles.get(style,styles['Bold']); out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    sub=str(Path(srt).resolve()).replace('\\','/').replace(':','\\:'); vf=f"subtitles='{sub}':force_style='{st}'"
    subprocess.run([ffmpeg,'-y','-i',video,'-vf',vf,'-c:v','libx264','-c:a','copy','-movflags','+faststart',str(out)],check=True)
    return str(out)
