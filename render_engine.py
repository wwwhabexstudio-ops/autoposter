"""Local-first FFmpeg render job definitions.

This module prepares deterministic render commands. Actual media assets can be
created by local/open-source generators or optional provider adapters.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from video_lab import VideoPlan

@dataclass
class RenderJob:
    project_dir: Path
    output_path: Path
    aspect_ratio: str
    width: int
    height: int


def create_render_job(plan: VideoPlan, project_dir: str = "data/projects") -> RenderJob:
    directory = Path(project_dir) / "renders"
    directory.mkdir(parents=True, exist_ok=True)
    safe = "".join(c.lower() if c.isalnum() else "_" for c in plan.title).strip("_")[:60] or "video"
    return RenderJob(directory, directory / f"{safe}_{plan.aspect_ratio.replace(':', 'x')}.mp4",
                     plan.aspect_ratio, plan.width, plan.height)
