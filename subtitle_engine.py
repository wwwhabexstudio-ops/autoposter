"""Simple subtitle generation from script sentences."""
from __future__ import annotations
from pathlib import Path
import re


def make_srt(text: str, duration_seconds: float, output: Path) -> Path:
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    sentences = sentences or [text.strip() or ""]
    per = duration_seconds / len(sentences)
    lines = []
    for i, sentence in enumerate(sentences, 1):
        start = i - 1
        end = i
        start_t = _timestamp(start * per)
        end_t = _timestamp(end * per)
        lines.append(f"{i}\n{start_t} --> {end_t}\n{sentence}\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _timestamp(seconds: float) -> str:
    h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = seconds % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s-int(s))*1000):03d}"
