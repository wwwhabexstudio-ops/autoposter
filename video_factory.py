"""Scene-based finished-video factory.

Builds a real MP4 from narration plus multiple visual scenes. When a
PEXELS_API_KEY is configured, each scene gets matching Pexels B-roll.
Without Pexels, deterministic animated visual cards are generated so the
video is never a black screen. Every scene is rendered for roughly 3-5s
with gentle Ken Burns motion.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _duration(audio: str) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe is required for scene timing")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return max(0.1, float(result.stdout.strip()))


def _safe_query(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    stop = {"the", "and", "that", "this", "with", "from", "they", "their", "about", "what", "when", "your", "into", "have", "people"}
    useful = [w for w in words if w not in stop and len(w) > 3]
    return " ".join(useful[:6]) or "documentary lifestyle"


def _pexels_image(query: str, orientation: str, destination: Path) -> Path | None:
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": key},
            params={"query": query, "per_page": 1, "orientation": orientation},
            timeout=20,
        )
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if not photos:
            return None
        src = photos[0].get("src", {})
        url = src.get("large2x") or src.get("large") or src.get("medium")
        if not url:
            return None
        data = requests.get(url, timeout=30)
        data.raise_for_status()
        destination.write_bytes(data.content)
        return destination
    except Exception:
        return None


def _font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _wrap(text: str, width: int = 34) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines[:7]


def _make_fallback_card(text: str, topic: str, width: int, height: int, path: Path, index: int) -> Path:
    digest = hashlib.md5(f"{topic}-{index}".encode()).hexdigest()
    base = tuple(35 + int(digest[i:i+2], 16) % 90 for i in (0, 2, 4))
    img = Image.new("RGB", (width, height), base)
    draw = ImageDraw.Draw(img, "RGBA")
    for n in range(6):
        x = int((n + 1) * width / 7)
        y = int((int(digest[(n * 2) % 24:(n * 2) % 24 + 2], 16) / 255) * height)
        radius = max(50, min(width, height) // 5)
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(255, 255, 255, 25), outline=(255, 255, 255, 45), width=4)
    draw.rounded_rectangle(
        (int(width*.08), int(height*.13), int(width*.92), int(height*.87)),
        radius=32, fill=(0, 0, 0, 95), outline=(255, 255, 255, 55), width=3,
    )
    title_font = _font(max(32, min(width, height)//13))
    body_font = _font(max(22, min(width, height)//25))
    draw.text((int(width*.12), int(height*.19)), f"SCENE {index:02d}", font=body_font, fill=(255, 255, 255, 190))
    y = int(height*.30)
    for line in _wrap(text, 29 if height > width else 48):
        draw.text((int(width*.12), y), line, font=title_font, fill=(255, 255, 255, 255))
        y += title_font.size + 12
    draw.text((int(width*.12), int(height*.78)), topic[:70], font=body_font, fill=(255, 255, 255, 180))
    img.save(path, quality=92)
    return path


def _make_scene_clip(image: Path, output: Path, width: int, height: int, seconds: float, index: int) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed on the host")
    frames = max(1, round(seconds * 30))
    zoom = "min(zoom+0.0007,1.08)" if index % 2 else "max(zoom-0.0005,1.0)"
    vf = (
        f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,"
        f"crop={width*2}:{height*2},"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={width}x{height}:fps=30,format=yuv420p"
    )
    _run([
        ffmpeg, "-y", "-loop", "1", "-i", str(image), "-t", f"{seconds:.3f}",
        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", str(output),
    ])


def _concat_clips(clips: list[Path], output: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    concat_file = output.with_suffix(".txt")
    concat_file.write_text(
        "\n".join(
            f"file '{p.as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'"
            for p in clips
        ),
        encoding="utf-8",
    )
    try:
        _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output)])
    finally:
        concat_file.unlink(missing_ok=True)


def _normalize_scenes(raw: list[dict], target_count: int, topic: str) -> list[dict]:
    """Split/merge narration blocks so visual changes occur about every 4 seconds."""
    text = " ".join(str(s.get("narration") or "") for s in raw).strip()
    words = text.split() or topic.split() or ["AutoPoster"]
    target_count = max(1, min(target_count, len(words)))
    base, extra = divmod(len(words), target_count)
    result: list[dict] = []
    cursor = 0
    for i in range(target_count):
        take = base + (1 if i < extra else 0)
        chunk = " ".join(words[cursor:cursor + take])
        cursor += take
        result.append({
            "scene": i + 1,
            "narration": chunk,
            "visual_prompt": f"cinematic documentary visual illustrating: {chunk[:260]}",
        })
    return result


def make_video(
    audio: str,
    output: str,
    width: int,
    height: int,
    duration: float | None = None,
    image: str | None = None,
    scenes: list[dict] | None = None,
    topic: str = "AutoPoster",
) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed on the host")
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / f".{out.stem}_scenes"
    work.mkdir(parents=True, exist_ok=True)

    audio_seconds = float(duration or _duration(audio))
    raw = scenes or ([{"scene": 1, "narration": topic}] if not image else [{"scene": 1, "narration": topic}])

    # Aim for one visual change every ~4 seconds. This intentionally splits
    # AI-generated scene blocks further when the AI returned too few scenes.
    target_count = max(1, round(audio_seconds / 4.0))
    selected = _normalize_scenes(raw, target_count, topic)
    if image and Path(image).exists() and len(selected) == 1:
        selected[0]["image"] = image

    # Keep normal scenes inside 3-5 seconds. The last scene absorbs tiny timing differences.
    if audio_seconds >= 3:
        per_scene = audio_seconds / len(selected)
        if per_scene < 3 or per_scene > 5:
            target_count = max(1, round(audio_seconds / 4.0))
            selected = _normalize_scenes(raw, target_count, topic)
        durations = [audio_seconds / len(selected)] * len(selected)
    else:
        durations = [audio_seconds]

    orientation = "portrait" if height > width else ("square" if height == width else "landscape")
    clips: list[Path] = []
    for idx, scene in enumerate(selected, start=1):
        narration = str(scene.get("narration") or scene.get("visual_prompt") or topic)
        img_path = work / f"scene_{idx:02d}.jpg"
        existing = scene.get("image") if scene.get("image") and Path(str(scene.get("image"))).exists() else None
        if existing:
            img_path = Path(str(existing))
        else:
            query = _safe_query(str(scene.get("visual_prompt") or narration))
            pexels = _pexels_image(query, orientation, img_path)
            if not pexels:
                _make_fallback_card(narration, topic, width, height, img_path, idx)
        clip = work / f"clip_{idx:02d}.mp4"
        _make_scene_clip(img_path, clip, width, height, durations[idx-1], idx)
        clips.append(clip)

    silent = work / "silent.mp4"
    _concat_clips(clips, silent)
    _run([
        ffmpeg, "-y", "-i", str(silent), "-i", audio, "-t", f"{audio_seconds:.3f}",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out),
    ])
    shutil.rmtree(work, ignore_errors=True)
    return str(out)
