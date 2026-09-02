"""Background AutoPoster generation worker.

Runs outside Streamlit so a browser reconnect/rerun does not cancel a long
Wan2.1 generation. The worker updates a JSON status file as it progresses.
"""
from __future__ import annotations
import json, shutil, subprocess, sys, time
from pathlib import Path

from script_engine import generate_script, generate_scene_plan_ai, fit_script_to_duration
from tts_engine import generate_voiceover
from video_factory import make_video

BASE_DIR=Path(__file__).parent
RENDER_DIR=BASE_DIR/"data"/"renders"; RENDER_DIR.mkdir(parents=True,exist_ok=True)
VIDEO_DIR=BASE_DIR/"data"/"videos"; VIDEO_DIR.mkdir(parents=True,exist_ok=True)


def write_status(path: Path, **data):
    payload={"updated_at":time.time(),**data}
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload),encoding="utf-8")
    tmp.replace(path)


def main(request_file: str):
    req_path=Path(request_file)
    req=json.loads(req_path.read_text(encoding="utf-8"))
    status_path=Path(req["status_file"])
    try:
        topic=str(req["topic"]); duration=int(req["duration"]); ratio=str(req["ratio"]); style=str(req["style"])
        script_mode=str(req["script_mode"]); script_input=str(req.get("script_input", ""))
        visual_mode=str(req.get("visual_mode", "text_to_video")); image_path=str(req.get("image_path", ""))
        job_id=str(req["job_id"])

        write_status(status_path,status="running",stage="script",message="Preparing narration script…",job_id=job_id)
        script=script_input.strip() if script_mode=="Paste script" else generate_script(topic,duration,style)
        script=fit_script_to_duration(script,duration)
        write_status(status_path,status="running",stage="scenes",message="Planning narration-matched scenes…",script=script,job_id=job_id)
        scenes=generate_scene_plan_ai(script,style)

        safe="_".join(topic.split())[:60] or "autoposter_video"
        stamp=int(time.time())
        audio=VIDEO_DIR/f"{safe}_{stamp}_voice.wav"
        video=RENDER_DIR/f"{safe}_{duration}s_{stamp}.mp4"
        write_status(status_path,status="running",stage="voice",message="Generating natural neural narration…",script=script,job_id=job_id)
        generate_voiceover(script,str(audio))

        ffprobe=shutil.which("ffprobe")
        if not ffprobe: raise RuntimeError("FFprobe is required")
        probe=subprocess.run([ffprobe,"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(audio)],check=True,capture_output=True,text=True)
        audio_seconds=float(probe.stdout.strip()); target_seconds=float(duration)

        if ratio.startswith("9:16"): w,h=720,1280
        elif ratio.startswith("1:1"): w,h=1080,1080
        else: w,h=1280,720
        render_seconds=min(audio_seconds,target_seconds)
        scene_count=max(1,round(render_seconds/4))
        if visual_mode=="image_animation":
            if not image_path or not Path(image_path).exists():
                raise RuntimeError("Image animation mode requires a valid uploaded image")
            video_message=f"Animating your image across {scene_count} REAL Wan2.1 I2V scenes…"
        else:
            video_message=f"Generating {scene_count} REAL Wan2.1 moving scenes…"
        write_status(status_path,status="running",stage="video",message=video_message,script=script,job_id=job_id,video=str(video),scene_count=scene_count,visual_mode=visual_mode)
        make_video(str(audio),str(video),w,h,duration=render_seconds,scenes=scenes,topic=topic,image=image_path or None,visual_mode=visual_mode)

        if not video.exists() or video.stat().st_size<=10000:
            raise RuntimeError("Wan2.1 render finished without producing a valid MP4")
        write_status(status_path,status="completed",stage="done",message="Video generation complete.",script=script,job_id=job_id,video=str(video),scene_count=scene_count,duration=render_seconds,visual_mode=visual_mode)
    except Exception as exc:
        write_status(status_path,status="failed",stage="error",message=str(exc),error=repr(exc),job_id=req.get("job_id"))
        raise


if __name__=="__main__":
    main(sys.argv[1])
