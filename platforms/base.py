from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PublishResult:
    success: bool
    platform: str
    remote_id: str | None = None
    url: str | None = None
    error: str | None = None


class PlatformAdapter(ABC):
    name: str

    @abstractmethod
    def publish(self, video_path: Path, title: str, description: str, hashtags: str) -> PublishResult:
        raise NotImplementedError
