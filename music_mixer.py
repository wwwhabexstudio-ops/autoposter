"""Automatic background-audio mixing with FFmpeg."""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path

def mix(narration:str, music:str, output:str, music_volume:float=0.12)->str:
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('FFmpeg is required')
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    cmd=[ffmpeg,'-y','-i',narration,'-stream_loop','-1','-i',music,'-filter_complex',f'[1:a]volume={music_volume}[m];[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]','-map','0:v?','-map','[a]','-c:a','aac','-shortest',str(out)]
    subprocess.run(cmd,check=True)
    return str(out)
