"""Platform-neutral performance scoring and posting-window analysis."""
from __future__ import annotations

from collections import defaultdict
from statistics import mean


def score_post(post: dict) -> float:
    """Compute a transparent score from normalized metrics, when available."""
    weights = {
        "retention_rate": 0.30,
        "engagement_rate": 0.25,
        "share_rate": 0.20,
        "follow_rate": 0.15,
        "click_rate": 0.10,
    }
    values = [(post.get(k), w) for k, w in weights.items() if post.get(k) is not None]
    if not values:
        return 0.0
    total_weight = sum(w for _, w in values)
    return round(sum(float(v) * w for v, w in values) / total_weight, 4)


def best_windows(posts: list[dict], min_samples: int = 3) -> list[dict]:
    """Rank weekday/hour buckets from observed results; never invent a window."""
    buckets = defaultdict(list)
    for p in posts:
        if p.get("weekday") is None or p.get("hour") is None:
            continue
        buckets[(p["weekday"], p["hour"])].append(score_post(p))
    ranked = [
        {"weekday": d, "hour": h, "samples": len(v), "score": round(mean(v), 4)}
        for (d, h), v in buckets.items() if len(v) >= min_samples
    ]
    return sorted(ranked, key=lambda x: x["score"], reverse=True)
