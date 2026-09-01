"""Natural-sounding local-first TTS using Piper neural voices."""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_PIPER_MODEL = "en_US-lessac-medium"


def _run(cmd, *, input_text: str | None = None):
    return subprocess.run(
        cmd,
        input=input_text,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def generate_voiceover(text: str, output: str, voice: str | None = None, rate: int = 165) -> str:
    """Generate a WAV voiceover with Piper.

    PIPER_MODEL may be either a local .onnx path or a Piper voice name. When a
    voice name is used, Piper downloads the voice automatically on first use.
    """
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    piper = os.getenv("PIPER_BIN") or shutil.which("piper")
    model = voice or os.getenv("PIPER_MODEL") or DEFAULT_PIPER_MODEL

    if not piper:
        # The piper-tts package exposes the same CLI as a Python module.
        try:
            subprocess.run(["python", "-m", "piper", "--help"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            piper_cmd = ["python", "-m", "piper"]
        except Exception as exc:
            raise RuntimeError("Piper neural TTS is not installed. Run: pip install piper-tts") from exc
    else:
        piper_cmd = [piper]

    wav = out.with_suffix(".wav")
    cmd = piper_cmd + ["--model", model, "--output_file", str(wav)]
    # Piper uses length_scale rather than a words-per-minute setting.
    cmd += ["--length_scale", str(max(0.65, min(1.35, 165 / max(rate, 1))))]

    try:
        _run(cmd, input_text=text)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        raise RuntimeError(f"Piper TTS failed: {detail[-800:]}") from exc

    if wav != out:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg is required for audio conversion")
        _run([ffmpeg, "-y", "-i", str(wav), "-ar", "44100", "-ac", "2", str(out)])
        wav.unlink(missing_ok=True)

    return str(out)
