"""Free/local-first text-to-speech wrapper."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path


def generate_voiceover(text: str, output: str, voice: str | None = None, rate: int = 165) -> str:
    """Use espeak-ng/espeak when installed. Returns output path.

    This intentionally avoids a paid API. Install a local TTS engine on the
    machine running AutoPoster for real speech generation.
    """
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("No local TTS engine found. Install espeak-ng or espeak on the host.")
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "-s", str(rate), "-w", str(out), text]
    if voice:
        cmd[1:1] = ["-v", voice]
    subprocess.run(cmd, check=True)
    return str(out)
