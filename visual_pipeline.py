"""Scene visual generation for AutoPoster.

Uses Pexels video B-roll when PEXELS_API_KEY is configured. When it is not,
we create non-black animated scene cards locally so the render still has
visual changes every 3-5 seconds.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "that", "this",
    "these", "those", "to", "of", "in", "on", "for", "with", "from", "into", "about",
    "are", "is", "was", "were", "be", "being", "been", "it", "its", "they", "their",
    "them", "you", "your", "we", "our", "people", "today", "often", "usually", "really",
    "just", "can", "could", "would", "should", "why", "what", "how", "when", "where",
}


def _keywords(text: str, limit: int = 7) -> str:
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    keep = []
    for word in words:
        if word in STOPWORDS or len(word) < 3:
            continue
        if word not in keep:
            keep.append(word)
        if len(keep) >= limit:
            break
    return " ".join(keep) or "documentary"


def _font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_motion_card(scene: dict, width: int, height: int, output_dir: Path) -> Path:
    """Create a unique visual card; video_factory adds subtle motion to it."""
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1((scene.get("narration", "") + str(scene.get("scene", ""))).encode()).hexdigest()[:10]
    path = output_dir / f"card_{scene.get('scene', 0)}_{digest}.png"
    if path.exists():
        return path

    seed = int(digest[:8], 16)
    base = (28 + seed % 55, 30 + (seed >> 8) % 50, 45 + (seed >> 16) % 55)
    img = Image.new("RGB", (width, height), base)
    draw = ImageDraw.Draw(img)

    for i in range(9):
        x = (seed * (i + 3) * 37) % width
        y = (seed * (i + 5) * 19) % height
        r = max(60, width // 5 + ((seed >> (i % 16)) % max(1, width // 5)))
        draw.ellipse((x-r, y-r, x+r, y+r), outline=(180, 180, 180), width=max(2, width // 360))

    scene_no = str(scene.get("scene", ""))
    title = _keywords(scene.get("narration", ""), 6).upper()
    draw.text((width * 0.08, height * 0.13), "SCENE " + scene_no, font=_font(max(26, width // 24)), fill=(235, 235, 235))

    words = title.split()
    lines, line = [], ""
    title_font = _font(max(42, width // 11))
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=title_font)[2] > width * 0.82 and line:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y = height * 0.42
    for text in lines[:4]:
        draw.text((width * 0.08, y), text, font=title_font, fill=(250, 250, 250))
        y += max(55, width // 9)

    narration = scene.get("narration", "").strip()
    if len(narration) > 150:
        narration = narration[:147].rsplit(" ", 1)[0] + "…"
    draw.text((width * 0.08, height * 0.78), narration, font=_font(max(20, width // 32)), fill=(210, 210, 210), spacing=10)
    img.save(path)
    return path


def _pexels_video(scene: dict, width: int, height: int, cache_dir: Path, index: int) -> Path | None:
    key = os.getenv("PEXELS_API_KEY", "").strip()
    if not key:
        return None

    cache_dir.mkdir(parents=True, exist_ok=True)
    query = _keywords(scene.get("visual_prompt") or scene.get("narration", ""), 7)
    digest = hashlib.sha1(query.encode()).hexdigest()[:12]
    candidates = sorted(cache_dir.glob(f"pexels_{digest}_*.mp4"))
    if candidates:
        return candidates[index % len(candidates)]

    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": key},
            params={
                "query": query,
                "per_page": 5,
                "orientation": "portrait" if height > width else "landscape",
            },
            timeout=30,
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])
        if not videos:
            return None

        ranked = []
        target_ratio = width / height
        for video in videos:
            for vf in video.get("video_files", []):
                link = vf.get("link")
                vw, vh = vf.get("width") or 0, vf.get("height") or 0
                if not link or not vw or not vh:
                    continue
                ratio_penalty = abs((vw / vh) - target_ratio)
                size_penalty = abs(vw - width) / max(width, 1)
                ranked.append((ratio_penalty + size_penalty * 0.2, link))
        if not ranked:
            return None
        ranked.sort(key=lambda x: x[0])

        for n, (_, link) in enumerate(ranked[:3]):
            target = cache_dir / f"pexels_{digest}_{n}.mp4"
            if target.exists():
                continue
            with requests.get(link, stream=True, timeout=90) as r:
                r.raise_for_status()
                with target.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
        candidates = sorted(cache_dir.glob(f"pexels_{digest}_*.mp4"))
        return candidates[index % len(candidates)] if candidates else None
    except Exception:
        return None


def get_scene_visual(scene: dict, width: int, height: int, cache_dir: Path, index: int) -> Path:
    clip = _pexels_video(scene, width, height, cache_dir / "pexels", index)
    if clip:
        return clip
    return make_motion_card(scene, width, height, cache_dir / "cards")
