from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from script_engine import generate_script, generate_scene_plan_ai
from tts_engine import generate_voiceover
from video_factory import make_video

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "data" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
RENDER_DIR = BASE_DIR / "data" / "renders"
RENDER_DIR.mkdir(parents=True, exist_ok=True)

# Streamlit Cloud / Secrets support without putting API keys in source code.
try:
    if st.secrets.get("PEXELS_API_KEY"):
        os.environ["PEXELS_API_KEY"] = str(st.secrets["PEXELS_API_KEY"])
except Exception:
    pass

st.set_page_config(page_title="AutoPoster", page_icon="📤", layout="wide")
st.title("📤 AutoPoster")
st.caption("Web-app test mode — create, preview and download videos directly")

st.info(
    "Google Colab / external GPU worker is disabled in this test build. "
    "The renderer now creates multiple synchronized visual scenes every ~3–5 seconds."
)

with st.form("create"):
    topic = st.text_input("Topic", placeholder="Why people are still poor")
    duration = st.slider("Duration", 15, 120, 30)
    ratio = st.selectbox("Aspect ratio", ["9:16 Vertical", "16:9 Landscape", "1:1 Square"])
    style = st.selectbox(
        "Style",
        ["Cinematic documentary", "Realistic", "Dark documentary", "Educational", "3D", "2D animated explainer"],
    )
    script_mode = st.radio("Script", ["Generate with AI", "Paste script"], horizontal=True)
    script_input = st.text_area("Script", height=220)
    generate = st.form_submit_button("🚀 Generate Video")

if generate:
    if not topic.strip():
        st.error("Enter a topic first.")
    else:
        try:
            script = script_input.strip() if script_mode == "Paste script" else generate_script(topic, int(duration), style)
            st.session_state["script"] = script

            st.subheader("📝 Script")
            st.text_area("Generated narration", script, height=260)

            with st.spinner("Planning scenes to match the narration…"):
                scenes = generate_scene_plan_ai(script, style)
            st.session_state["scenes"] = scenes

            st.subheader("🎬 Scene plan")
            st.json(scenes)
            st.caption("Each narration block becomes its own visual scene. The renderer keeps scenes around 3–5 seconds and trims the final video to the narration length.")

            safe = "_".join(topic.split())[:60]
            audio = VIDEO_DIR / f"{safe}_voice.wav"
            video = RENDER_DIR / f"{safe}.mp4"

            with st.spinner("Generating natural neural narration…"):
                generate_voiceover(script, str(audio))

            if ratio.startswith("9:16"):
                w, h = 720, 1280
            elif ratio.startswith("1:1"):
                w, h = 1080, 1080
            else:
                w, h = 1280, 720

            visual_note = "Pexels B-roll" if os.getenv("PEXELS_API_KEY") else "animated visual cards (add PEXELS_API_KEY for matching stock B-roll)"
            with st.spinner(f"Building synchronized scenes with {visual_note}…"):
                make_video(str(audio), str(video), w, h, scenes=scenes, topic=topic)

            st.session_state["generated_video"] = str(video)
            st.success("Video generated successfully with changing visual scenes.")
            st.video(str(video))
            st.download_button(
                "⬇️ Download video",
                video.read_bytes(),
                file_name=video.name,
                mime="video/mp4",
            )
        except Exception as e:
            st.error(f"Generation failed: {e}")

if st.session_state.get("generated_video"):
    st.divider()
    st.subheader("🎥 Current generated video")
    path = Path(st.session_state["generated_video"])
    if path.exists():
        st.video(str(path))
        st.download_button(
            "⬇️ Download current video",
            path.read_bytes(),
            file_name=path.name,
            mime="video/mp4",
            key="download_current",
        )
