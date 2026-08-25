import streamlit as st
from pathlib import Path
from datetime import datetime
import json

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
VIDEO_DIR = DATA_DIR / "videos"
QUEUE_FILE = DATA_DIR / "queue.json"

VIDEO_DIR.mkdir(parents=True, exist_ok=True)
if not QUEUE_FILE.exists():
    QUEUE_FILE.write_text("[]", encoding="utf-8")


def load_queue():
    try:
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_queue(queue):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")


st.set_page_config(page_title="AutoPoster", page_icon="📤", layout="wide")

st.title("📤 AutoPoster")
st.caption("Free multi-platform video publishing automation")

queue = load_queue()
videos = sorted(VIDEO_DIR.glob("*"))

col1, col2, col3 = st.columns(3)
col1.metric("Videos", len(videos))
col2.metric("Queued", len([x for x in queue if x.get("status") == "queued"]))
col3.metric("Published", len([x for x in queue if x.get("status") == "published"]))

st.divider()

st.subheader("Add a video")
upload = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "m4v"])

if upload:
    destination = VIDEO_DIR / upload.name
    destination.write_bytes(upload.getbuffer())
    st.success(f"Saved {upload.name}")

    if not any(item.get("filename") == upload.name for item in queue):
        queue.append({
            "filename": upload.name,
            "title": Path(upload.name).stem,
            "description": "",
            "hashtags": "",
            "platforms": ["youtube"],
            "scheduled_at": None,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat() + "Z",
        })
        save_queue(queue)

st.divider()
st.subheader("Publishing queue")

if not queue:
    st.info("No videos queued yet. Upload your first video above.")
else:
    for index, item in enumerate(queue):
        with st.expander(f"{item['filename']} — {item.get('status', 'queued')}"):
            item["title"] = st.text_input("Title", item.get("title", ""), key=f"title_{index}")
            item["description"] = st.text_area("Description", item.get("description", ""), key=f"desc_{index}")
            item["hashtags"] = st.text_input("Hashtags", item.get("hashtags", ""), key=f"tags_{index}")
            item["platforms"] = st.multiselect(
                "Platforms",
                ["youtube", "instagram", "facebook", "tiktok", "linkedin"],
                default=item.get("platforms", ["youtube"]),
                key=f"platforms_{index}",
            )
            if st.button("Save", key=f"save_{index}"):
                save_queue(queue)
                st.success("Saved")

st.divider()
st.subheader("Platform connections")
st.info("API connections will be added next. We will use official platform APIs and never store your social passwords in this app.")

st.caption("AutoPoster V0.1 — built for a $0 workflow")
