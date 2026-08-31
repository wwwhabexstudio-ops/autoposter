"""Natural-sounding local-first TTS. Neural engines are preferred; eSpeak is never used for production."""
from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path

def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def generate_voiceover(text: str, output: str, voice: str | None = None, rate: int = 165) -> str:
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    # Piper: lightweight neural TTS. Configure PIPER_BIN and PIPER_MODEL in Secrets/env.
    piper=os.getenv('PIPER_BIN') or shutil.which('piper')
    model=os.getenv('PIPER_MODEL')
    if piper and model and Path(model).exists():
        wav=out.with_suffix('.wav')
        _run([piper,'--model',model,'--output_file',str(wav), '--length_scale',str(max(.65,min(1.35,165/max(rate,1))))], input=None) if False else None
        # Piper reads text from stdin.
        p=subprocess.run([piper,'--model',model,'--output_file',str(wav)],input=text,text=True,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if wav != out:
            ffmpeg=shutil.which('ffmpeg')
            if not ffmpeg: raise RuntimeError('FFmpeg required for audio conversion')
            _run([ffmpeg,'-y','-i',str(wav),'-ar','44100','-ac','2',str(out)]); wav.unlink(missing_ok=True)
        return str(out)
    # macOS built-in voice is acceptable development fallback.
    say=shutil.which('say')
    if say:
        aiff=out.with_suffix('.aiff'); _run([say,'-o',str(aiff),text]); ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg: raise RuntimeError('FFmpeg required to convert macOS TTS audio')
        _run([ffmpeg,'-y','-i',str(aiff),'-ar','44100','-ac','2',str(out)]); aiff.unlink(missing_ok=True); return str(out)
    raise RuntimeError('Neural TTS is not configured. Install Piper and set PIPER_MODEL; robotic eSpeak is intentionally disabled.')
