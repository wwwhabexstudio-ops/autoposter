from __future__ import annotations
import json, os, shutil, subprocess, time, uuid
from pathlib import Path
import streamlit as st
from script_engine import generate_script, generate_scene_plan_ai, fit_script_to_duration
from motion_worker import wan_available

BASE_DIR=Path(__file__).parent
VIDEO_DIR=BASE_DIR/"data"/"videos"; VIDEO_DIR.mkdir(parents=True,exist_ok=True)
RENDER_DIR=BASE_DIR/"data"/"renders"; RENDER_DIR.mkdir(parents=True,exist_ok=True)
LATEST_STATE=RENDER_DIR/".latest_video.json"
JOB_STATE=RENDER_DIR/".generation_job.json"

try:
    if st.secrets.get("MOTION_WORKER_URL"): os.environ["MOTION_WORKER_URL"]=str(st.secrets["MOTION_WORKER_URL"])
except Exception: pass

st.set_page_config(page_title="AutoPoster",page_icon="📤",layout="wide")
st.title("📤 AutoPoster")
st.caption("AI video generation — Wan2.1 T2V + synchronized narration")


def _read_job():
    try:
        if JOB_STATE.exists():
            return json.loads(JOB_STATE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _save_latest_video(path: Path, topic: str, duration: float) -> None:
    payload={"path":str(path),"topic":topic,"duration":duration,"completed_at":time.time()}
    tmp=LATEST_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload),encoding="utf-8")
    tmp.replace(LATEST_STATE)
    st.session_state["generated_video"]=str(path)


def _recover_latest_video() -> Path|None:
    try:
        if LATEST_STATE.exists():
            data=json.loads(LATEST_STATE.read_text(encoding="utf-8"))
            candidate=Path(str(data.get("path", "")))
            if candidate.exists() and candidate.suffix.lower()==".mp4" and candidate.stat().st_size>10000:
                return candidate
    except Exception:
        pass
    renders=sorted(RENDER_DIR.glob("*.mp4"),key=lambda p:p.stat().st_mtime,reverse=True)
    for candidate in renders:
        try:
            if candidate.stat().st_size>10000: return candidate
        except OSError: pass
    return None


def _launch_generation(topic, duration, ratio, style, script_mode, script_input):
    job_id=uuid.uuid4().hex[:12]
    request_file=RENDER_DIR/f".generation_request_{job_id}.json"
    payload={"job_id":job_id,"topic":topic,"duration":int(duration),"ratio":ratio,"style":style,"script_mode":script_mode,"script_input":script_input,"status_file":str(JOB_STATE)}
    request_file.write_text(json.dumps(payload),encoding="utf-8")
    JOB_STATE.write_text(json.dumps({"status":"running","stage":"starting","message":"Starting background generation…","job_id":job_id}),encoding="utf-8")
    subprocess.Popen([__import__("sys").executable,str(BASE_DIR/"generation_worker.py"),str(request_file)],cwd=str(BASE_DIR),start_new_session=True)
    st.session_state["active_job_id"]=job_id


if not st.session_state.get("generated_video"):
    recovered=_recover_latest_video()
    if recovered: st.session_state["generated_video"]=str(recovered)

wan_ok, wan_source=wan_available()
if wan_ok:
    if wan_source.startswith("local:"):
        st.success(f"🟢 Wan2.1 connected: {wan_source[6:]}. Every scene will be generated as real moving video.")
    else:
        st.success(f"🟢 Wan2.1 remote generation connected: {wan_source}. AutoPoster will generate real moving clips automatically — no worker URL required.")
else:
    st.info(f"🔵 Wan2.1 remote mode is enabled. Connection check: {wan_source}. AutoPoster will try the official Wan2.1 service when you generate.")

job=_read_job()
if job and job.get("status")=="running":
    st.warning(f"⏳ Generation is still running — {job.get('message','Please wait…')}")
    if job.get("stage")=="video":
        st.progress(0.75,text="Wan2.1 is rendering real moving scenes…")
    else:
        st.progress(0.15,text="Preparing your video…")
    st.caption("The Wan2.1 worker is running outside Streamlit, so refreshing or reconnecting will not cancel generation.")
    time.sleep(2)
    st.rerun()

if job and job.get("status")=="completed" and job.get("video"):
    completed=Path(job["video"])
    if completed.exists() and completed.stat().st_size>10000:
        _save_latest_video(completed,job.get("topic",""),float(job.get("duration",0) or 0))
        JOB_STATE.unlink(missing_ok=True)
        try: Path(job.get("request_file", "")).unlink(missing_ok=True)
        except Exception: pass
        st.success(f"✅ Video ready — {job.get('scene_count','')} real Wan2.1 moving scenes generated.")

with st.form("create"):
    topic=st.text_input("Topic",placeholder="Why people are still poor")
    duration=st.slider("Duration",15,120,30)
    ratio=st.selectbox("Aspect ratio",["9:16 Vertical","16:9 Landscape","1:1 Square"])
    style=st.selectbox("Visual style",["Cinematic documentary","Realistic","Dark documentary","Educational","3D"])
    script_mode=st.radio("Script",["Generate with AI","Paste script"],horizontal=True)
    script_input=st.text_area("Script",height=220)
    generate=st.form_submit_button("🚀 Generate Real Wan2.1 Video")

if generate:
    if not topic.strip():
        st.error("Enter a topic first.")
    elif job and job.get("status")=="running":
        st.warning("A video is already generating. Please wait for it to finish.")
    else:
        try:
            _launch_generation(topic.strip(),int(duration),ratio,style,script_mode,script_input)
            st.rerun()
        except Exception as e:
            st.error(f"Could not start generation: {e}")

current=Path(st.session_state.get("generated_video","")) if st.session_state.get("generated_video") else _recover_latest_video()
if current and current.exists():
    st.session_state["generated_video"]=str(current)
    st.divider(); st.subheader("🎥 Current generated video")
    st.caption("Latest video is saved and remains available after refreshes, reconnects, and Streamlit reruns.")
    st.video(str(current))
    st.download_button("⬇️ Download current video",current.read_bytes(),file_name=current.name,mime="video/mp4",key="download_current")
