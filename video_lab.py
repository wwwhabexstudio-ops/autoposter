"""Provider-neutral video generation and assembly planning."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

SUPPORTED_ASPECT_RATIOS = {"16:9": (1920, 1080), "9:16": (1080, 1920)}

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
    aspect_ratio: str = "16:9"
    width: int = 1920
    height: int = 1080

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

def plan_video(title: str, script: str, duration_seconds: int = 60,
               format_name: str = "short-form", aspect_ratio: str = "16:9") -> VideoPlan:
    """Create a scene plan for short or long-form video in 16:9 or 9:16."""
    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        raise ValueError("aspect_ratio must be '16:9' or '9:16'")
    if duration_seconds < 1:
        raise ValueError("duration_seconds must be positive")
    width, height = SUPPORTED_ASPECT_RATIOS[aspect_ratio]
    sentences = [s.strip() for s in script.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    count = max(1, min(len(sentences), max(1, duration_seconds // 8)))
    selected = sentences[:count] or [title]
    per_scene = duration_seconds / len(selected)
    scenes = [Scene(i + 1, text, f"Cinematic visual supporting: {text}. Compose safely for {aspect_ratio}.", round(per_scene, 2)) for i, text in enumerate(selected)]
    return VideoPlan(title, format_name, duration_seconds, scenes, aspect_ratio=aspect_ratio, width=width, height=height)
