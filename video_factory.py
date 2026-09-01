"""Scene-based MP4 renderer for AutoPoster.

Every narration scene gets its own visual clip. Pexels video is used when a
PEXELS_API_KEY is configured; otherwise unique animated scene cards are used.
The scene durations are derived from the narration/audio duration and kept in
the 3-5 second range whenever the source is long enough.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from visual_pipeline import get_scene_visual


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _probe_duration(path: str) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("FFprobe is not installed on the host")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return float(result.stdout.strip())


def _scene_count(audio_duration: float, requested: int | None = None) -> int:
    if requested:
        return max(1, requested)
    if audio_duration <= 5:
        return 1
    return max(1, int(round(audio_duration / 4.2)))


def build_scenes(narration: str, audio_duration: float, requested: int | None = None) -> list[dict]:
    """Split narration into short visual beats and assign audio-aligned durations."""
    words = narration.split()
    if not words:
        return [{"scene": 1, "narration": "", "visual_prompt": "documentary establishing shot", "duration_seconds": audio_duration}]

    count = min(_scene_count(audio_duration, requested), 80)
    if audio_duration >= 3:
        count = min(count, max(1, math.floor(audio_duration / 3)))

    chunks: list[str] = []
    for i in range(count):
        start = round(i * len(words) / count)
        end = round((i + 1) * len(words) / count)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)

    if not chunks:
        chunks = [narration]

    total_words = len(words)
    raw = [audio_duration * len(c.split()) / total_words for c in chunks]
    durations = [min(5.0, max(3.0, d)) for d in raw]

    # Keep the total video aligned to the audio. For very long audio, the last
    # scene can absorb the remainder after all other scenes reach five seconds.
    delta = audio_duration - sum(durations)
    if delta > 0:
        for i in range(len(durations)):
            add = min(delta, 5.0 - durations[i])
            durations[i] += add
            delta -= add
            if delta <= 0.01:
                break
        if delta > 0.01:
            durations[-1] += delta
    elif delta < 0:
        for i in range(len(durations)):
            sub = min(-delta, max(0.0, durations[i] - 3.0))
            durations[i] -= sub
            delta += sub
            if delta >= -0.01:
                break
        if delta < -0.01:
            durations[-1] = max(0.1, durations[-1] + delta)

    return [
        {
            "scene": i + 1,
            "narration": chunk,
            "visual_prompt": f"cinematic documentary B-roll illustrating: {chunk[:220]}",
            "duration_seconds": round(max(0.1, duration), 3),
        }
        for i, (chunk, duration) in enumerate(zip(chunks, durations))
    ]


def _render_scene_clip(source: Path, output: Path, width: int, height: int, duration: float) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed on the host")

    if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        frames = max(1, round(duration * 30))
        vf = (
            f"scale={width*12//10}:{height*12//10}:force_original_aspect_ratio=increase,"
            f"crop={width*12//10}:{height*12//10},"
            f"zoompan=z='min(zoom+0.0015,1.08)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=30,"
            "setsar=1,format=yuv420p"
        )
        cmd = [ffmpeg, "-y", "-loop", "1", "-i", str(source), "-vf", vf, "-t", f"{duration:.3f}",
               "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30", str(output)]
    else:
        vf = (
            f"scale={width*12//10}:{height*12//10}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,format=yuv420p"
        )
        cmd = [ffmpeg, "-y", "-stream_loop", "-1", "-i", str(source), "-vf", vf, "-t", f"{duration:.3f}",
               "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30", str(output)]
    _run(cmd)


def make_video(
    audio: str,
    output: str,
    width: int,
    height: int,
    duration: float | None = None,
    image: str | None = None,
    scenes: list[dict] | None = None,
    narration: str | None = None,
) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is not installed on the host")
    if not Path(audio).exists():
        raise RuntimeError(f"Narration audio not found: {audio}")

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    audio_duration = float(duration or _probe_duration(audio))

    if not scenes:
        if image and Path(image).exists():
            scenes = [{"scene": 1, "narration": narration or "", "visual_prompt": "documentary", "duration_seconds": audio_duration, "image": image}]
        elif narration:
            scenes = build_scenes(narration, audio_duration)
        else:
            scenes = [{"scene": 1, "narration": "", "visual_prompt": "documentary", "duration_seconds": audio_duration}]

    cache_dir = out.parent.parent / "scene_assets"
    with tempfile.TemporaryDirectory(prefix="autoposter_render_") as tmp:
        tmpdir = Path(tmp)
        clip_paths = []
        for idx, scene in enumerate(scenes):
            source = Path(scene["image"]) if scene.get("image") else get_scene_visual(scene, width, height, cache_dir, idx)
            clip = tmpdir / f"scene_{idx:04d}.mp4"
            _render_scene_clip(source, clip, width, height, float(scene.get("duration_seconds", 4)))
            clip_paths.append(clip)

        concat_list = tmpdir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'" for p in clip_paths),
            encoding="utf-8",
        )
        visual = tmpdir / "visual.mp4"
        _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", "-an", str(visual)])

        _run([
            ffmpeg, "-y", "-i", str(visual), "-i", audio,
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-shortest", "-movflags", "+faststart", "-pix_fmt", "yuv420p", str(out)
        ])
    return str(out)
