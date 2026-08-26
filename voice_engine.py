"""Voiceover abstraction with a local pyttsx3 backend when available."""
from __future__ import annotations
from pathlib import Path


def available() -> bool:
    try:
        import pyttsx3  # noqa: F401
        return True
    except ImportError:
        return False


def synthesize(text: str, output: Path, rate: int = 165) -> Path:
    try:
        import pyttsx3
    except ImportError as exc:
        raise RuntimeError("Install pyttsx3 for the free local voiceover engine.") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.save_to_file(text, str(output))
    engine.runAndWait()
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("The local voice engine did not produce an audio file.")
    return output
