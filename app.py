from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path
import streamlit as st

from database import add_post, list_posts, update_post
from content_pipeline import create_project
from video_lab import SUPPORTED_ASPECT_RATIOS

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "data" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
PLATFORMS = ["youtube", "instagram", "facebook", "tiktok", "linkedin"]

st.set_page_config(page_title="AutoPoster", page_icon="📤", layout="wide")
st.title("📤 AutoPoster")
st.caption("Free multi-platform content, video planning and publishing automation")

posts = list_posts()
video_count = len(list(VIDEO_DIR.glob("*")))
queued = len([p for p in posts if p["status"] in ("queued", "publishing")])
published = len([p for p in posts if p["status"] == "published"])
failed = len([p for p in posts if p["status"] == "failed"])

c1, c2, c3, c4 = st.columns(4)
c1.metric("Videos", video_count)
c2.metric("Queued", queued)
c3.metric("Published", published)
c4.metric("Failed", failed)

st.divider()
st.subheader("🎬 Video Lab")
with st.form("video_lab"):
    topic = st.text_input("Topic", placeholder="Why people stay broke after getting a raise")
    video_type = st.selectbox("Video type", ["Short-form", "Long-form"])
    aspect_ratio = st.selectbox("Aspect ratio", list(SUPPORTED_ASPECT_RATIOS.keys()), index=0)
    default_duration = 45 if video_type == "Short-form" else 600
    duration = st.number_input("Target duration (seconds)", min_value=10, max_value=7200, value=default_duration, step=10)
    script = st.text_area("Script / draft narration", placeholder="Paste a draft script here. Later the AI research layer will generate this for you.")
    title = st.text_input("Working title", value=topic)
    caption = st.text_area("Caption / description", placeholder="Platform-specific captions will be generated later.")
    gen_platforms = st.multiselect("Target platforms", PLATFORMS, default=["youtube"])
    generate = st.form_submit_button("🧠 Create video project")

if generate:
    if not topic.strip():
        st.error("Enter a topic first.")
    elif not script.strip():
        st.warning("Add a draft script for now. The AI research/script generator is the next generation layer.")
    else:
        project = create_project(topic, script, video_type.lower(), int(duration), title, caption=caption, platforms=gen_platforms)
        project.video_plan.aspect_ratio = aspect_ratio
        project.video_plan.width, project.video_plan.height = SUPPORTED_ASPECT_RATIOS[aspect_ratio]
        saved = project.save()
        st.success("Video project created.")
        st.json({"project_file": saved, "format": video_type, "aspect_ratio": aspect_ratio, "duration_seconds": int(duration), "scenes": len(project.video_plan.scenes)})

st.divider()
st.subheader("1. Add a finished video")
upload = st.file_uploader("Upload MP4/MOV/M4V", type=["mp4", "mov", "m4v"])
if upload:
    destination = VIDEO_DIR / upload.name
    if not destination.exists():
        destination.write_bytes(upload.getbuffer())
        st.success(f"Saved {upload.name}")
    else:
        st.info("That filename already exists; using the existing file.")
    with st.form("new_post"):
        title = st.text_input("Title", Path(upload.name).stem)
        description = st.text_area("Description")
        hashtags = st.text_input("Hashtags", placeholder="#money #business #youtube")
        platforms = st.multiselect("Platforms", PLATFORMS, default=["youtube"])
        schedule_mode = st.radio("When?", ["Schedule", "Queue without a time"], horizontal=True)
        scheduled_at = None
        if schedule_mode == "Schedule":
            d = st.date_input("Date", value=date.today())
            t = st.time_input("Time", value=time(20, 0))
            scheduled_at = datetime.combine(d, t).replace(tzinfo=timezone.utc).isoformat()
        submitted = st.form_submit_button("Add to publishing queue")
    if submitted:
        if not platforms:
            st.error("Choose at least one platform.")
        else:
            now = datetime.now(timezone.utc).isoformat()
            add_post({"filename": upload.name, "title": title, "description": description, "hashtags": hashtags, "platforms": platforms, "scheduled_at": scheduled_at, "status": "queued", "created_at": now, "updated_at": now})
            st.success("Added to the queue.")
            st.rerun()

st.divider()
st.subheader("2. Publishing queue")
posts = list_posts()
if not posts:
    st.info("No posts yet. Upload your first video above.")
else:
    for post in posts:
        with st.expander(f"#{post['id']} • {post['filename']} • {post['status']}"):
            st.write(f"**Platforms:** {post['platforms']}")
            st.write(f"**Scheduled:** {post['scheduled_at'] or 'Not scheduled'}")
            st.write(f"**Title:** {post['title']}")
            if post.get("last_error"): st.error(post["last_error"])
            if post.get("platform_results") and post["platform_results"] != "{}": st.code(post["platform_results"], language="json")
            if post["status"] in ("queued", "failed") and st.button("Retry / keep queued", key=f"retry_{post['id']}"):
                update_post(post["id"], status="queued", last_error="")
                st.rerun()

st.divider()
st.subheader("3. Platform status")
for name, value in {
    "YouTube": "🟢 Adapter installed — OAuth required",
    "Instagram": "🟡 Meta API required",
    "Facebook": "🟡 Meta API required",
    "TikTok": "🟡 TikTok app approval required",
    "LinkedIn": "🟡 LinkedIn API access required",
}.items():
    st.write(f"**{name}:** {value}")
st.caption("Official APIs only. Never put social passwords or API tokens in source code.")
