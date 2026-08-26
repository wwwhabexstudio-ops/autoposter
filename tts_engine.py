"""Free/local-first text-to-speech wrapper with platform fallbacks."""
from __future__ import annotations
import shutil, subprocess
from pathlib import Path

def generate_voiceover(text: str, output: str, voice: str | None = None, rate: int = 165) -> str:
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    exe=shutil.which('espeak-ng') or shutil.which('espeak')
    if exe:
        cmd=[exe,'-s',str(rate),'-w',str(out)]
        if voice: cmd[1:1]=['-v', 'en-us+m3' if voice.lower()=='male' else 'en-us+f3']
        cmd.append(text); subprocess.run(cmd,check=True); return str(out)
    say=shutil.which('say')
    if say:
        aiff=out.with_suffix('.aiff'); subprocess.run([say,'-o',str(aiff),text],check=True)
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg: raise RuntimeError('FFmpeg required to convert macOS TTS audio')
        subprocess.run([ffmpeg,'-y','-i',str(aiff),str(out)],check=True); aiff.unlink(missing_ok=True); return str(out)
    raise RuntimeError('No local TTS engine. Run setup.sh in the Codespace or configure a TTS provider.')
