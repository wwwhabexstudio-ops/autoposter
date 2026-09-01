from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import os, json
import streamlit as st
from database import add_post, list_posts, update_post
from content_pipeline import create_project
from video_lab import SUPPORTED_ASPECT_RATIOS
from youtube_adapter import authorization_url, finish_authorization, credentials, upload_video
from youtube_analytics import channel_summary, analytics_report
from tts_engine import generate_voiceover
from video_factory import make_video
from script_engine import generate_script, scene_plan
from platform_intelligence import generate_metadata, analyze
from brand_overlay import add_logo

BASE_DIR=Path(__file__).parent; VIDEO_DIR=BASE_DIR/"data"/"videos"; RENDER_DIR=BASE_DIR/"data"/"renders"; ASSET_DIR=BASE_DIR/"data"/"assets"
for d in (VIDEO_DIR,RENDER_DIR,ASSET_DIR): d.mkdir(parents=True,exist_ok=True)
PLATFORMS=["youtube","instagram","facebook","tiktok","linkedin"]
st.set_page_config(page_title="AutoPoster",page_icon="📤",layout="wide")
st.title("📤 AutoPoster"); st.caption("Free/local-first AI content creation, rendering, analytics and publishing")
params=st.query_params
if params.get("code") and params.get("state"):
    try:
        redirect=os.getenv("AUTPOSTER_REDIRECT_URI") or st.secrets.get("AUTPOSTER_REDIRECT_URI")
        if not redirect: raise RuntimeError("AUTPOSTER_REDIRECT_URI is not configured")
        if st.session_state.get("oauth_state") != params.get("state"): raise RuntimeError("OAuth state mismatch")
        finish_authorization(redirect,str(params.get("code")),str(params.get("state"))); st.session_state["youtube_connected"]=True; st.query_params.clear(); st.success("YouTube connected successfully."); st.rerun()
    except Exception as e: st.error(f"YouTube authorization failed: {e}")

posts=list_posts(); video_count=len(list(RENDER_DIR.glob("*.mp4"))); queued=len([p for p in posts if p["status"] in ("queued","publishing")]); published=len([p for p in posts if p["status"]=="published"]); failed=len([p for p in posts if p["status"]=="failed"])
c1,c2,c3,c4=st.columns(4); c1.metric("Videos",video_count); c2.metric("Queued",queued); c3.metric("Published",published); c4.metric("Failed",failed)

st.divider(); st.subheader("🎬 Create Video")
with st.form("create_video"):
    topic=st.text_input("Topic",placeholder="Why people stay broke after getting a raise")
    platforms=st.multiselect("Platforms",PLATFORMS,default=["youtube"])
    video_type=st.selectbox("Video type",["Short-form","Long-form"])
    ratio=st.selectbox("Aspect ratio",list(SUPPORTED_ASPECT_RATIOS.keys()))
    duration=st.number_input("Duration (seconds)",10,7200,45 if video_type=="Short-form" else 660,10)
    style=st.selectbox("Video style",["Cinematic documentary","Realistic","3D","UGC","News","Educational","Dark documentary","Luxury","Anime"])
    script_mode=st.radio("Script",["Generate with AI","Paste my script"],horizontal=True)
    script_input=st.text_area("Script / narration",placeholder="Paste your script here" if script_mode=="Paste my script" else "Optional: leave empty to generate automatically")
    voice=st.selectbox("Voice",["Female","Male"])
    logo=st.file_uploader("Brand logo (optional)",type=["png","jpg","jpeg"])
    generate=st.form_submit_button("🚀 Generate Video")
if generate:
    try:
        script=script_input.strip() if script_mode=="Paste my script" else generate_script(topic,int(duration),style)
        if not topic.strip() or not script: raise ValueError("Topic and script are required")
        st.session_state["generated_script"]=script
        project=create_project(topic,script,video_type.lower(),int(duration),topic,platforms=platforms); project.video_plan.aspect_ratio=ratio; project.video_plan.width,project.video_plan.height=SUPPORTED_ASPECT_RATIOS[ratio]; saved=project.save()
        st.success("Script and scene plan generated."); st.text_area("Generated script",script,height=250)
        st.json({"scenes":scene_plan(script),"project_file":saved})
        audio=VIDEO_DIR/(Path(topic.replace(' ','_')).stem+"_voice.wav"); base=RENDER_DIR/(Path(topic.replace(' ','_')).stem+".mp4")
        generate_voiceover(script,str(audio)); w,h=SUPPORTED_ASPECT_RATIOS[ratio]; make_video(str(audio),str(base),w,h)
        final=base
        if logo:
            lp=ASSET_DIR/("brand_logo"+Path(logo.name).suffix); lp.write_bytes(logo.getbuffer()); branded=RENDER_DIR/(base.stem+"_branded.mp4"); add_logo(str(base),str(lp),str(branded)); final=branded
        st.success(f"Finished MP4 created: {final.name}"); st.video(str(final)); st.download_button("⬇️ Download video",final.read_bytes(),file_name=final.name,mime="video/mp4")
        for p in platforms:
            m=generate_metadata(topic,script,p); st.write(f"**{p.title()}** — {m.title}"); st.caption(m.caption); st.code(" ".join(m.tags))
    except Exception as e: st.error(f"Generation failed: {e}")

st.divider(); st.subheader("⚡ Free GPU Video Generation")
st.caption("Optional: connect a Google Colab T4 running the AutoPoster Wan2.1 worker. This produces genuine moving video clips, not a zoom/pan over a still image.")
try:
    from gpu_client import health as gpu_health, generate_clip
    gpu_url=os.getenv("GPU_WORKER_URL","")
    if gpu_url:
        if st.button("🔌 Check GPU worker"):
            try:
                info=gpu_health(); st.success(f"GPU online: {info.get('gpu') or 'unknown'} • {info.get('model','')}")
            except Exception as e: st.error(f"GPU worker unavailable: {e}")
        if st.button("🎞️ Generate 5-second AI scene"):
            try:
                prompt=f"{style.lower()} video, cinematic documentary visual about {topic}, natural continuous motion, clear subject action, detailed environment, smooth camera movement, consistent visual style, no text, no subtitles, no watermark"
                w,h=SUPPORTED_ASPECT_RATIOS[ratio]
                out=RENDER_DIR/(Path(topic.replace(' ','_')).stem+"_ai_scene.mp4")
                with st.spinner("Generating a real AI video scene on the GPU worker…"):
                    generate_clip(prompt,str(out),seconds=5,width=w,height=h,steps=20)
                st.success("AI scene generated."); st.video(str(out)); st.download_button("⬇️ Download AI scene",out.read_bytes(),file_name=out.name,mime="video/mp4")
            except Exception as e: st.error(f"GPU generation failed: {e}")
    else:
        st.info("Set GPU_WORKER_URL after starting the Colab worker to enable real AI video generation.")
except Exception as e: st.warning(f"GPU worker client unavailable: {e}")

st.divider(); st.subheader("📤 Upload Existing Video")
upload=st.file_uploader("Upload MP4/MOV/M4V",type=["mp4","mov","m4v"])
if upload:
    destination=VIDEO_DIR/upload.name
    if not destination.exists(): destination.write_bytes(upload.getbuffer())
    with st.form("new_post"):
        ptitle=st.text_input("Title",Path(upload.name).stem); description=st.text_area("Description"); hashtags=st.text_input("Hashtags"); target=st.multiselect("Platforms",PLATFORMS,default=["youtube"]); scheduled_at=None
        if st.form_submit_button("Add to publishing queue"):
            now=datetime.now(timezone.utc).isoformat(); add_post({"filename":upload.name,"title":ptitle,"description":description,"hashtags":hashtags,"platforms":target,"scheduled_at":scheduled_at,"status":"queued","created_at":now,"updated_at":now}); st.success("Added to queue."); st.rerun()

st.divider(); st.subheader("📊 Analytics & AI Learning")
try:
    connected=credentials() is not None
except Exception: connected=False
if connected:
    try:
        ch=channel_summary(); stats=ch.get('statistics',{}); a,b,c=st.columns(3); a.metric("Subscribers",stats.get('subscriberCount','0')); b.metric("Channel views",stats.get('viewCount','0')); c.metric("Videos",stats.get('videoCount','0'))
        if st.button("Refresh analytics"):
            report=analytics_report(28); st.json(report)
            st.info("AI recommendation: use above-average videos as the reference for the next hook, topic and format; test one variable at a time.")
    except Exception as e: st.warning(str(e))
else: st.info("Connect YouTube below to activate live analytics.")

st.divider(); st.subheader("🚀 YouTube Publishing")
if connected: st.success("YouTube connected")
else:
    try: redirect=os.getenv("AUTPOSTER_REDIRECT_URI") or st.secrets.get("AUTPOSTER_REDIRECT_URI")
    except Exception: redirect=os.getenv("AUTPOSTER_REDIRECT_URI")
    if redirect and st.button("Connect YouTube"):
        url,state=authorization_url(redirect); st.session_state["oauth_state"]=state; st.link_button("Continue to Google authorization",url)
    elif not redirect: st.warning("Set AUTPOSTER_REDIRECT_URI to enable YouTube OAuth.")

st.subheader("Publishing queue")
for post in list_posts():
    with st.expander(f"#{post['id']} • {post['filename']} • {post['status']}"):
        st.write(f"Platforms: {post['platforms']} | Scheduled: {post['scheduled_at'] or 'Now'}")
        if connected and "youtube" in post["platforms"] and st.button("Upload to YouTube (private)",key=f"yt_{post['id']}"):
            try:
                result=upload_video(str(VIDEO_DIR/post["filename"]),post["title"],post.get("description","")+"\n"+post.get("hashtags","") ,"private"); update_post(post["id"],status="published",platform_results=json.dumps({"youtube":result}),last_error=""); st.success(f"Uploaded privately: {result.get('id','')}"); st.rerun()
            except Exception as e: update_post(post["id"],status="failed",last_error=str(e)); st.error(str(e))

st.divider(); st.subheader("Platform status")
for n,s in {"YouTube":"🟢 OAuth/upload/analytics","Instagram":"🟡 Meta credentials + permissions required","Facebook":"🟡 Meta credentials + permissions required","TikTok":"🟡 App approval/credentials required","LinkedIn":"🟡 API access/credentials required"}.items(): st.write(f"**{n}:** {s}")
st.caption("Official APIs only. Never put social passwords or API tokens in source code.")
