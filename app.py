from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path
import streamlit as st
from script_engine import generate_script, generate_scene_plan_ai, fit_script_to_duration
from tts_engine import generate_voiceover
from video_factory import make_video

BASE_DIR=Path(__file__).parent
VIDEO_DIR=BASE_DIR/"data"/"videos"; VIDEO_DIR.mkdir(parents=True,exist_ok=True)
RENDER_DIR=BASE_DIR/"data"/"renders"; RENDER_DIR.mkdir(parents=True,exist_ok=True)

try:
    if st.secrets.get("PEXELS_API_KEY"): os.environ["PEXELS_API_KEY"]=str(st.secrets["PEXELS_API_KEY"])
    if st.secrets.get("MOTION_WORKER_URL"): os.environ["MOTION_WORKER_URL"]=str(st.secrets["MOTION_WORKER_URL"])
except Exception: pass

st.set_page_config(page_title="AutoPoster",page_icon="📤",layout="wide")
st.title("📤 AutoPoster")
st.caption("AI video test mode — Wan2.1 motion scenes + synchronized narration")

worker=os.getenv("MOTION_WORKER_URL")
if worker:
    st.success("🟢 Wan2.1 AI video worker connected — every visual scene is generated as real moving video.")
else:
    st.warning("🟡 Wan2.1 worker is not connected. The app will use Pexels/animated fallback visuals. Set MOTION_WORKER_URL to use the real AI video model.")

with st.form("create"):
    topic=st.text_input("Topic",placeholder="Why people are still poor")
    duration=st.slider("Duration",15,120,30)
    ratio=st.selectbox("Aspect ratio",["9:16 Vertical","16:9 Landscape","1:1 Square"])
    style=st.selectbox("Style",["Cinematic documentary","Realistic","Dark documentary","Educational","3D","2D animated explainer"])
    script_mode=st.radio("Script",["Generate with AI","Paste script"],horizontal=True)
    script_input=st.text_area("Script",height=220)
    generate=st.form_submit_button("🚀 Generate Video")

if generate:
    if not topic.strip(): st.error("Enter a topic first.")
    else:
        try:
            script=script_input.strip() if script_mode=="Paste script" else generate_script(topic,int(duration),style)
            # Enforce the selected duration for both generated and pasted scripts.
            script=fit_script_to_duration(script,int(duration))
            st.session_state["script"]=script
            st.subheader("📝 Script")
            st.text_area("Narration",script,height=220)

            with st.spinner("Planning semantic scenes…"):
                scenes=generate_scene_plan_ai(script,style)
            st.session_state["scenes"]=scenes

            safe="_".join(topic.split())[:60]
            audio=VIDEO_DIR/f"{safe}_voice.wav"; video=RENDER_DIR/f"{safe}.mp4"
            with st.spinner("Generating natural neural narration…"):
                generate_voiceover(script,str(audio))

            ffprobe=shutil.which("ffprobe")
            if not ffprobe: raise RuntimeError("FFprobe is required for accurate scene timing")
            probe=subprocess.run([ffprobe,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(audio)],check=True,capture_output=True,text=True)
            audio_seconds=float(probe.stdout.strip())

            if ratio.startswith("9:16"): w,h=720,1280
            elif ratio.startswith("1:1"): w,h=1080,1080
            else: w,h=1280,720

            scene_count=max(1,round(audio_seconds/4))
            st.subheader(f"🎬 Visual timeline — {scene_count} scenes")
            st.caption(f"One new visual about every 4 seconds. Final duration follows the {audio_seconds:.1f}s narration.")
            st.dataframe([{ "Scene":i+1,"Target":f"{audio_seconds/scene_count:.1f}s","Narration":(scenes[i % len(scenes)].get("narration","") if scenes else "") } for i in range(scene_count)],use_container_width=True,hide_index=True)

            mode="Wan2.1 real AI motion" if worker else ("Pexels B-roll" if os.getenv("PEXELS_API_KEY") else "animated fallback")
            with st.spinner(f"Generating {scene_count} synchronized scenes with {mode}…"):
                make_video(str(audio),str(video),w,h,scenes=scenes,topic=topic)

            st.session_state["generated_video"]=str(video)
            st.success(f"Video generated successfully — {scene_count} changing visual scenes.")
            st.video(str(video))
            st.download_button("⬇️ Download video",video.read_bytes(),file_name=video.name,mime="video/mp4")
        except Exception as e:
            st.error(f"Generation failed: {e}")

if st.session_state.get("generated_video"):
    st.divider(); st.subheader("🎥 Current generated video")
    path=Path(st.session_state["generated_video"])
    if path.exists():
        st.video(str(path))
        st.download_button("⬇️ Download current video",path.read_bytes(),file_name=path.name,mime="video/mp4",key="download_current")
