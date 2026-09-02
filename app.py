from __future__ import annotations
import json, os, shutil, subprocess, time
from pathlib import Path
import streamlit as st
from script_engine import generate_script, generate_scene_plan_ai, fit_script_to_duration
from tts_engine import generate_voiceover
from video_factory import make_video
from motion_worker import wan_available

BASE_DIR=Path(__file__).parent
VIDEO_DIR=BASE_DIR/"data"/"videos"; VIDEO_DIR.mkdir(parents=True,exist_ok=True)
RENDER_DIR=BASE_DIR/"data"/"renders"; RENDER_DIR.mkdir(parents=True,exist_ok=True)
LATEST_STATE=RENDER_DIR/".latest_video.json"

try:
    if st.secrets.get("MOTION_WORKER_URL"): os.environ["MOTION_WORKER_URL"]=str(st.secrets["MOTION_WORKER_URL"])
except Exception: pass

st.set_page_config(page_title="AutoPoster",page_icon="📤",layout="wide")
st.title("📤 AutoPoster")
st.caption("AI video generation — Wan2.1 T2V + synchronized narration")


def _save_latest_video(path: Path, topic: str, duration: float) -> None:
    """Persist the completed render outside Streamlit session state.

    Streamlit can rerun/reconnect during a long AI render. The manifest lets the
    next page run recover the completed MP4 instead of returning to a blank
    dashboard.
    """
    payload={"path":str(path),"topic":topic,"duration":duration,"completed_at":time.time()}
    tmp=LATEST_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload),encoding="utf-8")
    tmp.replace(LATEST_STATE)
    st.session_state["generated_video"]=str(path)


def _recover_latest_video() -> Path|None:
    """Recover the newest completed render after a Streamlit rerun/reconnect."""
    try:
        if LATEST_STATE.exists():
            data=json.loads(LATEST_STATE.read_text(encoding="utf-8"))
            candidate=Path(str(data.get("path", "")))
            if candidate.exists() and candidate.suffix.lower()==".mp4" and candidate.stat().st_size>0:
                return candidate
    except Exception:
        pass
    # Fallback recovery if the manifest was interrupted before being written.
    renders=sorted(RENDER_DIR.glob("*.mp4"),key=lambda p:p.stat().st_mtime,reverse=True)
    for candidate in renders:
        try:
            if candidate.stat().st_size>0:
                return candidate
        except OSError:
            continue
    return None


# Restore the last completed video whenever Streamlit starts/reruns.
if not st.session_state.get("generated_video"):
    recovered=_recover_latest_video()
    if recovered:
        st.session_state["generated_video"]=str(recovered)

wan_ok, wan_source=wan_available()
if wan_ok:
    if wan_source.startswith("local:"):
        st.success(f"🟢 Wan2.1 connected: {wan_source[6:]}. Every scene will be generated as real moving video.")
    else:
        st.success(f"🟢 Wan2.1 remote generation connected: {wan_source}. AutoPoster will generate real moving clips automatically — no worker URL required.")
else:
    st.info(f"🔵 Wan2.1 remote mode is enabled. Connection check: {wan_source}. AutoPoster will try the official Wan2.1 service when you generate.")

with st.form("create"):
    topic=st.text_input("Topic",placeholder="Why people are still poor")
    duration=st.slider("Duration",15,120,30)
    ratio=st.selectbox("Aspect ratio",["9:16 Vertical","16:9 Landscape","1:1 Square"])
    style=st.selectbox("Style",["Cinematic documentary","Realistic","Dark documentary","Educational","3D","2D animated explainer"])
    script_mode=st.radio("Script",["Generate with AI","Paste script"],horizontal=True)
    script_input=st.text_area("Script",height=220)
    generate=st.form_submit_button("🚀 Generate Wan2.1 Video")

if generate:
    if not topic.strip(): st.error("Enter a topic first.")
    else:
        try:
            script=script_input.strip() if script_mode=="Paste script" else generate_script(topic,int(duration),style)
            script=fit_script_to_duration(script,int(duration))
            st.session_state["script"]=script
            st.subheader("📝 Script")
            st.text_area("Narration",script,height=220)

            with st.spinner("Planning narration-matched scenes…"):
                scenes=generate_scene_plan_ai(script,style)
            st.session_state["scenes"]=scenes

            safe="_".join(topic.split())[:60]
            # Include a timestamp so each successful render is a distinct, persistent artifact.
            stamp=int(time.time())
            audio=VIDEO_DIR/f"{safe}_{stamp}_voice.wav"; video=RENDER_DIR/f"{safe}_{int(duration)}s_{stamp}.mp4"
            with st.spinner("Generating natural neural narration…"):
                generate_voiceover(script,str(audio))

            ffprobe=shutil.which("ffprobe")
            if not ffprobe: raise RuntimeError("FFprobe is required")
            probe=subprocess.run([ffprobe,"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(audio)],check=True,capture_output=True,text=True)
            audio_seconds=float(probe.stdout.strip())
            target_seconds=float(duration)

            if ratio.startswith("9:16"): w,h=720,1280
            elif ratio.startswith("1:1"): w,h=1080,1080
            else: w,h=1280,720

            render_seconds=min(audio_seconds,target_seconds)
            scene_count=max(1,round(render_seconds/4))
            st.subheader(f"🎬 Wan2.1 visual timeline — {scene_count} scenes")
            st.caption(f"Fresh moving AI visual approximately every 3–5 seconds. Target: {target_seconds:.0f}s; narration: {audio_seconds:.1f}s; render: {render_seconds:.1f}s.")
            st.dataframe([{"Scene":i+1,"Target":f"{render_seconds/scene_count:.1f}s","Narration":(scenes[i].get("narration","") if i<len(scenes) else "")} for i in range(scene_count)],use_container_width=True,hide_index=True)

            with st.spinner(f"Generating {scene_count} REAL Wan2.1 moving scenes…"):
                make_video(str(audio),str(video),w,h,duration=render_seconds,scenes=scenes,topic=topic)

            if not video.exists() or video.stat().st_size==0:
                raise RuntimeError("Wan2.1 render finished without producing a valid MP4")

            # Persist completion BEFORE displaying the video. This survives a
            # Streamlit rerun/reconnect immediately after the long render.
            _save_latest_video(video,topic,render_seconds)
            st.success(f"Done — {scene_count} Wan2.1 moving scenes synchronized to the narration.")
            st.video(str(video))
            st.download_button("⬇️ Download video",video.read_bytes(),file_name=video.name,mime="video/mp4",key="download_new")
        except Exception as e:
            st.error(f"Generation failed: {e}")

# Always show the latest completed render, even after a Streamlit rerun/reconnect.
current=Path(st.session_state.get("generated_video","")) if st.session_state.get("generated_video") else _recover_latest_video()
if current and current.exists():
    st.session_state["generated_video"]=str(current)
    st.divider(); st.subheader("🎥 Current generated video")
    st.caption("Your latest completed video is saved and will remain available after page reruns or reconnections.")
    st.video(str(current))
    st.download_button("⬇️ Download current video",current.read_bytes(),file_name=current.name,mime="video/mp4",key="download_current")
