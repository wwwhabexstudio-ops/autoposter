"""Platform-agnostic content intelligence and metadata generation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class PlatformAdvice:
    platform: str
    title: str
    caption: str
    tags: list[str]
    hook: str


def generate_metadata(topic: str, script: str, platform: str) -> PlatformAdvice:
    p=platform.lower()
    hook=f"Nobody tells you this about {topic.lower()}"
    if p == "youtube":
        title=f"{hook.title()}"
        caption=f"{script[:700]}\n\nSubscribe for more videos about this topic."
        tags=["#youtube", "#money", "#personalfinance"]
    elif p == "tiktok":
        title=hook
        caption=f"{hook}. Watch until the end."
        tags=["#fyp", "#money", "#mindset"]
    elif p == "instagram":
        title=hook
        caption=f"{hook}. Save this and share it with someone who needs to hear it."
        tags=["#reels", "#money", "#mindset"]
    else:
        title=hook.title(); caption=script[:500]; tags=["#content", "#video"]
    return PlatformAdvice(p,title,caption,tags,hook)


def analyze(metrics: list[dict[str,Any]]) -> dict[str,Any]:
    if not metrics: return {"status":"Need more data", "recommendations":[]}
    views=[float(x.get("views",0)) for x in metrics]
    avg=sum(views)/len(views)
    top=sorted(metrics,key=lambda x:float(x.get("views",0)),reverse=True)[:5]
    return {"status":"learning", "videos":len(metrics), "average_views":avg, "top_videos":top,
            "recommendations":["Reuse hooks/topics from above-average videos", "Test one variable at a time", "Keep platform-specific metadata separate"]}
