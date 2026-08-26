"""High-level content production pipeline for short and long-form projects."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

from video_lab import plan_video, VideoPlan


@dataclass
class ContentProject:
    topic: str
    format: str
    target_duration_seconds: int
    title: str
    hook: str
    script: str
    caption: str
    platforms: list[str]
    video_plan: VideoPlan

    def save(self, directory: str = "data/projects") -> str:
        path = Path(directory) / self.safe_name()
        path.mkdir(parents=True, exist_ok=True)
        (path / "project.json").write_text(
            json.dumps(asdict(self), indent=2), encoding="utf-8"
        )
        return str(path / "project.json")

    def safe_name(self) -> str:
        cleaned = "".join(c.lower() if c.isalnum() else "_" for c in self.topic)
        return cleaned.strip("_")[:80] or "untitled"


def create_project(topic: str, script: str, format_name: str = "long-form",
                   duration_seconds: int = 600,
                   title: str | None = None,
                   hook: str | None = None,
                   caption: str = "",
                   platforms: list[str] | None = None) -> ContentProject:
    title = title or topic
    hook = hook or f"The truth about {topic} that most people miss."
    platforms = platforms or ["youtube"]
    vp = plan_video(title, script, duration_seconds, format_name)
    return ContentProject(topic, format_name, duration_seconds, title, hook,
                          script, caption, platforms, vp)
