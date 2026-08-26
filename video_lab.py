"""Provider-neutral video generation/assembly pipeline.

The core pipeline is intentionally free/local-first: it plans scenes, creates
an edit manifest, and can assemble media with FFmpeg. External AI video/TTS
providers can be plugged in later without changing the scheduler or UI.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json


@dataclass
class Scene:
    number: int
    narration: str
    visual_prompt: str
    duration_seconds: float
    asset: str | None = None


@dataclass
class VideoPlan:
    title: str
    format: str
    target_duration_seconds: int
    scenes: list[Scene]
    voice: str = "default"
    aspect_ratio: str = "9:16"

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def plan_video(title: str, script: str, duration_seconds: int = 60,
               format_name: str = "short-form", aspect_ratio: str = "9:16") -> VideoPlan:
    """Create a scene plan from a script. Generation is provider-independent."""
    sentences = [s.strip() for s in script.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    count = max(1, min(len(sentences), int(max(1, duration_seconds // 8))))
    selected = sentences[:count]
    per_scene = duration_seconds / len(selected)
    scenes = [
        Scene(i + 1, text, f"Cinematic visual supporting: {text}", round(per_scene, 2))
        for i, text in enumerate(selected)
    ]
    return VideoPlan(title, format_name, duration_seconds, scenes, aspect_ratio=aspect_ratio)
