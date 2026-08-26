from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from database import get_due_posts, update_post
from platforms.youtube import YouTubeAdapter

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "data" / "videos"

ADAPTERS = {"youtube": YouTubeAdapter()}


def run_once() -> None:
    now = datetime.now(timezone.utc).isoformat()
    for post in get_due_posts(now):
        video_path = VIDEO_DIR / post["filename"]
        if not video_path.exists():
            update_post(post["id"], status="failed", last_error=f"Video not found: {video_path}")
            continue

        update_post(post["id"], status="publishing")
        results = {}
        failures = []
        for platform in [p.strip() for p in post["platforms"].split(",") if p.strip()]:
            adapter = ADAPTERS.get(platform)
            if not adapter:
                results[platform] = {"success": False, "error": "Platform adapter not enabled yet"}
                failures.append(platform)
                continue
            result = adapter.publish(video_path, post["title"], post["description"], post["hashtags"])
            results[platform] = result.__dict__
            if not result.success:
                failures.append(platform)

        update_post(
            post["id"],
            status="failed" if failures else "published",
            last_error=("Failed platforms: " + ", ".join(failures)) if failures else "",
            platform_results=json.dumps(results),
        )


if __name__ == "__main__":
    run_once()
