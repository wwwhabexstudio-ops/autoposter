from __future__ import annotations
from datetime import date, datetime, time, timezone
from pathlib import Path
import os, json
import streamlit as st

from database import add_post, list_posts, update_post
from content_pipeline import create_project
from video_lab import SUPPORTED_ASPECT_RATIOS
from youtube_adapter import authorization_url, finish_authorization, credentials, upload_video
from youtube_analytics import channel_summary, analytics_report
from tts_engine import generate_voiceover

BASE_DIR=Path(__file__).parent; VIDEO_DIR=BASE_DIR/"data"/"videos"; RENDER_DIR=BASE_DIR/"data"/"renders"; VIDEO_DIR.mkdir(parents=True,exist_ok=True); RENDER_DIR.mkdir(parents=True,exist_ok=True)
PLATFORMS=["youtube","instagram","facebook","tiktok","linkedin"]
st.set_page_config(page_title="AutoPoster",page_icon="📤",layout="wide")
st.title("📤 AutoPoster"); st.caption("Free multi-platform content, video planning and publishing automation")

# OAuth callback handler. Set AUTPOSTER_REDIRECT_URI to the exact HTTPS callback URL.
params=st.query_params
if params.get("code") and params.get("state"):
    try:
        redirect=os.getenv("AUTPOSTER_REDIRECT_URI") or st.secrets.get("AUTPOSTER_REDIRECT_URI")
        if not redirect: raise RuntimeError("AUTPOSTER_REDIRECT_URI is not configured")
        if st.session_state.get("oauth_state") != params.get("state"): raise RuntimeError("OAuth state mismatch")
        finish_authorization(redirect,str(params.get("code")),str(params.get("state")))
        st.session_state["youtube_connected"]=True; st.query_params.clear(); st.success("YouTube connected successfully."); st.rerun()
    except Exception as e: st.error(f"YouTube authorization failed: {e}")

posts=list_posts(); video_count=len(list(VIDEO_DIR.glob("*"))); queued=len([p for p in posts if p["status"] in ("queued","publishing")]); published=len([p for p in posts if p["status"]=="published"]); failed=len([p for p in posts if p["status"]=="failed"])
c1,c2,c3,c4=st.columns(4); c1.metric("Videos",video_count); c2.metric("Queued",queued); c3.metric("Published",published); c4.metric("Failed",failed)

st.divider(); st.subheader("🎬 Video Lab")
with st.form("video_lab"):
    topic=st.text_input("Topic",placeholder="Why people stay broke after getting a raise")
    video_type=st.selectbox("Video type",["Short-form","Long-form"])
    aspect_ratio=st.selectbox("Aspect ratio",list(SUPPORTED_ASPECT_RATIOS.keys()),index=0)
    default_duration=45 if video_type=="Short-form" else 600
    duration=st.number_input("Target duration (seconds)",min_value=10,max_value=7200,value=default_duration,step=10)
    script=st.text_area("Script / narration",placeholder="Write or paste narration. The automatic AI writer can be connected to a local LLM later.")
    title=st.text_input("Working title",value=topic)
    caption=st.text_area("Caption / description")
    gen_platforms=st.multiselect("Target platforms",PLATFORMS,default=["youtube"])
    generate=st.form_submit_button("🧠 Create video project")
if generate:
    if not topic.strip() or not script.strip(): st.error("Enter a topic and narration first.")
    else:
        project=create_project(topic,script,video_type.lower(),int(duration),title,caption=caption,platforms=gen_platforms); project.video_plan.aspect_ratio=aspect_ratio; project.video_plan.width,project.video_plan.height=SUPPORTED_ASPECT_RATIOS[aspect_ratio]; saved=project.save(); st.session_state["last_project"]=project; st.success("Video project created."); st.json({"project_file":saved,"format":video_type,"aspect_ratio":aspect_ratio,"duration_seconds":int(duration),"scenes":len(project.video_plan.scenes)})

st.subheader("🎙️ Voiceover")
voice_text=st.text_area("Voiceover text",value=script if 'script' in locals() else "",key="voice_text")
if st.button("Generate local voiceover"):
    try:
        out=VIDEO_DIR/"voiceover.wav"; generate_voiceover(voice_text,str(out)); st.success(f"Voiceover created: {out.name}"); st.audio(str(out))
    except Exception as e: st.error(str(e))

st.divider(); st.subheader("1. Add a finished video")
upload=st.file_uploader("Upload MP4/MOV/M4V",type=["mp4","mov","m4v"])
if upload:
    destination=VIDEO_DIR/upload.name
    if not destination.exists(): destination.write_bytes(upload.getbuffer()); st.success(f"Saved {upload.name}")
    with st.form("new_post"):
        ptitle=st.text_input("Title",Path(upload.name).stem); description=st.text_area("Description"); hashtags=st.text_input("Hashtags"); platforms=st.multiselect("Platforms",PLATFORMS,default=["youtube"]); schedule_mode=st.radio("When?",["Schedule","Queue without a time"],horizontal=True); scheduled_at=None
        if schedule_mode=="Schedule":
            d=st.date_input("Date",value=date.today()); t=st.time_input("Time",value=time(20,0)); scheduled_at=datetime.combine(d,t).replace(tzinfo=timezone.utc).isoformat()
        submitted=st.form_submit_button("Add to publishing queue")
    if submitted:
        if not platforms: st.error("Choose at least one platform.")
        else:
            now=datetime.now(timezone.utc).isoformat(); add_post({"filename":upload.name,"title":ptitle,"description":description,"hashtags":hashtags,"platforms":platforms,"scheduled_at":scheduled_at,"status":"queued","created_at":now,"updated_at":now}); st.success("Added to queue."); st.rerun()

st.divider(); st.subheader("🚀 YouTube")
try:
    connected=credentials() is not None
except Exception: connected=False
if connected:
    st.success("YouTube connected")
    try:
        ch=channel_summary(); st.write(f"**{ch['snippet']['title']}** — {ch.get('statistics',{}).get('subscriberCount','0')} subscribers")
        if st.button("Refresh YouTube analytics"):
            st.json(analytics_report(28))
    except Exception as e: st.warning(str(e))
else:
    try:
        redirect=os.getenv("AUTPOSTER_REDIRECT_URI") or st.secrets.get("AUTPOSTER_REDIRECT_URI")
    except Exception: redirect=os.getenv("AUTPOSTER_REDIRECT_URI")
    if redirect:
        if st.button("🔴 Connect YouTube"):
            url,state=authorization_url(redirect); st.session_state["oauth_state"]=state; st.link_button("Continue to Google authorization",url)
    else: st.warning("Set AUTPOSTER_REDIRECT_URI to enable YouTube OAuth.")

st.divider(); st.subheader("2. Publishing queue")
posts=list_posts()
if not posts: st.info("No posts yet. Upload your first video above.")
for post in posts:
    with st.expander(f"#{post['id']} • {post['filename']} • {post['status']}"):
        st.write(f"**Platforms:** {post['platforms']}"); st.write(f"**Scheduled:** {post['scheduled_at'] or 'Not scheduled'}"); st.write(f"**Title:** {post['title']}")
        if post.get("last_error"): st.error(post["last_error"])
        if "youtube" in post["platforms"].split(",") and connected and st.button("Upload to YouTube (private)",key=f"yt_{post['id']}"):
            try:
                result=upload_video(str(VIDEO_DIR/post["filename"]),post["title"],post.get("description","")+"\n"+post.get("hashtags","") ,"private"); update_post(post["id"],status="published",platform_results=json.dumps({"youtube":result}),last_error=""); st.success(f"Uploaded to YouTube: {result.get('id','')}"); st.rerun()
            except Exception as e: update_post(post["id"],status="failed",last_error=str(e)); st.error(str(e))
        if post["status"] in ("queued","failed") and st.button("Retry / keep queued",key=f"retry_{post['id']}"): update_post(post["id"],status="queued",last_error=""); st.rerun()

st.divider(); st.subheader("3. Platform status")
for name,value in {"YouTube":"🟢 OAuth + upload adapter installed","Instagram":"🟡 Meta API required","Facebook":"🟡 Meta API required","TikTok":"🟡 TikTok app approval required","LinkedIn":"🟡 LinkedIn API access required"}.items(): st.write(f"**{name}:** {value}")
st.caption("Official APIs only. Never put social passwords or API tokens in source code.")
