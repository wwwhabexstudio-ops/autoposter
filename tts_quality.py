"""Natural-voice TTS adapter with local-first options."""
from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path

def synthesize(text: str, output: str, voice: str='female') -> str:
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    # Prefer Piper if installed: neural TTS is substantially clearer than espeak.
    piper=shutil.which('piper')
    model=os.getenv('PIPER_MODEL')
    if piper and model:
        subprocess.run([piper,'--model',model,'--output_file',str(out)],input=text.encode(),check=True)
        return str(out)
    # Coqui TTS CLI can be configured externally; keep the adapter optional.
    tts=os.getenv('TTS_COMMAND')
    if tts:
        subprocess.run(tts.format(text=text.replace('"','\\"'),output=str(out),voice=voice),shell=True,check=True)
        return str(out)
    raise RuntimeError('No neural TTS configured. Install Piper and set PIPER_MODEL, or configure TTS_COMMAND. Espeak is only a fallback and is intentionally not used as the quality voice.')
