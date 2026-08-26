"""Platform-aware content planning and optimization engine.
Zero-cost deterministic baseline; replace the template generator with an LLM later.
"""
from __future__ import annotations
import re
from typing import Any

PLATFORM_RULES = {
    "youtube": {"title_max": 100, "caption_max": 5000},
    "instagram": {"title_max": 0, "caption_max": 2200},
    "tiktok": {"title_max": 0, "caption_max": 2200},
    "facebook": {"title_max": 255, "caption_max": 63206},
    "linkedin": {"title_max": 200, "caption_max": 3000},
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def generate_metadata(topic: str, script: str = "", platform: str = "youtube") -> dict[str, Any]:
    topic = _clean(topic)
    script = _clean(script)
    hook = f"Nobody tells you this about {topic.lower()}"
    title = f"Why {topic} — And What You Should Do Instead"
    if platform == "youtube":
        caption = f"{hook}.\n\nIn this video, we break down {topic.lower()} and the practical lessons you can use.\n\nWatch until the end for the key takeaway."
        tags = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", topic) if len(w) > 3][:8]
    elif platform == "tiktok":
        caption = f"{hook} 👀\n
Save this and share it with someone who needs to hear it."
        tags = ["#fyp", "#learnontiktok"] + [f"#{w.lower()}" for w in re.findall(r"[A-Za-z0-9]+", topic)[:3]]
    elif platform == "instagram":
        caption = f"{hook}.\n\nHere's the part most people miss: {topic.lower()}.\n\nSave this for later and send it to someone who needs it."
        tags = [f"#{w.lower()}" for w in re.findall(r"[A-Za-z0-9]+", topic)[:5]]
    else:
        caption = f"{hook}.\n\n{topic} — practical lessons, examples, and next steps."
        tags = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", topic) if len(w) > 3][:8]
    rule = PLATFORM_RULES.get(platform, PLATFORM_RULES["youtube"])
    return {"hook": hook, "title": title[: rule["title_max"] or None], "caption": caption[:rule["caption_max"]], "tags": tags}


def learn_from_metrics(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics:
        return {"status": "not_enough_data", "recommendations": ["Publish at least 5 videos to establish a baseline."]}
    views = [float(m.get("views", 0) or 0) for m in metrics]
    likes = [float(m.get("likes", 0) or 0) for m in metrics]
    comments = [float(m.get("comments", 0) or 0) for m in metrics]
    avg_views = sum(views) / len(views)
    avg_engagement = sum((l+c)/max(v,1) for v,l,c in zip(views,likes,comments)) / len(metrics)
    best = max(metrics, key=lambda m: float(m.get("views",0) or 0))
    return {"status":"ready", "videos_analyzed":len(metrics), "average_views":round(avg_views), "average_engagement_rate":round(avg_engagement*100,2), "best_video":best, "recommendations":["Study the hook and topic of the highest-view video.", "Keep a consistent format while testing one variable at a time.", "Use platform-specific metadata instead of copying one caption everywhere."]}
