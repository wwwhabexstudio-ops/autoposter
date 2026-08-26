from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path

import streamlit as st

from database import add_post, list_posts, update_post

BASE_DIR = Path(__file__).parent
VIDEO_DIR = BASE_DIR / "data" / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

PLATFORMS = ["youtube", "instagram", "facebook", "tiktok", "linkedin"]

st.set_page_config(page_title="AutoPoster", page_icon="📤", layout="wide")
st.title("📤 AutoPoster")
st.caption("Free multi-platform video publishing automation")

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
st.subheader("1. Add a video")
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
            st.caption("Times are stored as UTC. We will add a user timezone setting next.")
        submitted = st.form_submit_button("Add to publishing queue")

    if submitted:
        if not platforms:
            st.error("Choose at least one platform.")
        else:
            now = datetime.now(timezone.utc).isoformat()
            add_post({
                "filename": upload.name,
                "title": title,
                "description": description,
                "hashtags": hashtags,
                "platforms": platforms,
                "scheduled_at": scheduled_at,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
            })
            st.success("Added to the queue.")
            st.rerun()

st.divider()
st.subheader("2. Publishing queue")
posts = list_posts()

if not posts:
    st.info("No posts yet. Upload your first video above.")
else:
    for post in posts:
        label = f"#{post['id']} • {post['filename']} • {post['status']}"
        with st.expander(label):
            st.write(f"**Platforms:** {post['platforms']}")
            st.write(f"**Scheduled:** {post['scheduled_at'] or 'Not scheduled'}")
            st.write(f"**Title:** {post['title']}")
            if post.get("last_error"):
                st.error(post["last_error"])
            if post.get("platform_results") and post["platform_results"] != "{}":
                st.code(post["platform_results"], language="json")
            if post["status"] in ("queued", "failed"):
                if st.button("Retry / keep queued", key=f"retry_{post['id']}"):
                    update_post(post["id"], status="queued", last_error="")
                    st.rerun()

st.divider()
st.subheader("3. Platform status")
status = {
    "YouTube": "🟢 Adapter installed — OAuth required",
    "Instagram": "🟡 Adapter next — Meta API required",
    "Facebook": "🟡 Adapter next — Meta API required",
    "TikTok": "🟡 Adapter next — TikTok app approval required",
    "LinkedIn": "🟡 Adapter next — LinkedIn API access required",
}
for name, value in status.items():
    st.write(f"**{name}:** {value}")

st.caption("AutoPoster — official APIs only. Never put social passwords or API tokens in source code.")
