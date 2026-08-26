"""YouTube channel/video analytics helpers."""
from __future__ import annotations
from datetime import date, timedelta
from youtube_adapter import service, analytics_service

def channel_summary() -> dict:
    data = service().channels().list(part="snippet,statistics", mine=True).execute()
    item = (data.get("items") or [None])[0]
    if not item: raise RuntimeError("No YouTube channel found for this account")
    return item

def video_stats(video_ids: list[str]) -> list[dict]:
    if not video_ids: return []
    return service().videos().list(part="snippet,statistics,contentDetails", id=','.join(video_ids)).execute().get("items", [])

def analytics_report(days: int = 28) -> dict:
    end = date.today(); start = end - timedelta(days=max(1, days))
    return analytics_service().reports().query(
        ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
        metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments,subscribersGained"
    ).execute()
