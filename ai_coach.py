"""Content intelligence primitives for AutoPoster.

This module turns observed post metrics into explainable recommendations.
It does not claim to control recommendation algorithms.
"""
from __future__ import annotations

from statistics import mean


def summarize_posts(posts: list[dict]) -> dict:
    published = [p for p in posts if p.get("status") == "published"]
    if not published:
        return {"sample_size": 0}

    durations = [p.get("duration_seconds") for p in published if p.get("duration_seconds")]
    engagement = [p.get("engagement_rate") for p in published if p.get("engagement_rate") is not None]
    return {
        "sample_size": len(published),
        "avg_duration": round(mean(durations), 1) if durations else None,
        "avg_engagement_rate": round(mean(engagement), 4) if engagement else None,
    }


def recommendation(summary: dict) -> str:
    if summary.get("sample_size", 0) < 5:
        return "Collect at least 5 published results before making strong performance recommendations."
    return "Use the strongest observed patterns as experiments for the next batch; keep testing rather than assuming a universal best time."
