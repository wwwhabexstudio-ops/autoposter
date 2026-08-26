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
from script_engine import generate_script, generate_scene_plan_ai
from platform_intelligence import generate_metadata
from brand_overlay import add_logo
from image_video_pipeline import render_from_scenes

BASE_DIR=Path(__file__).parent; VIDEO_DIR=BASE_DIR/'data'/'videos'; RENDER_DIR=BASE_DIR/'data'/'renders'; ASSET_DIR=BASE_DIR/'data'/'assets'; CLIP_DIR=BASE_DIR/'data'/'clips'
for d in (VIDEO_DIR,RENDER_DIR,ASSET_DIR,CLIP_DIR): d.mkdir(parents=True,exist_ok=True)
PLATFORMS=['youtube','instagram','facebook','tiktok','linkedin']
st.set_page_config(page_title='AutoPoster',page_icon='📤',layout='wide')
st.title('📤 AutoPoster'); st.caption('Free-first AI content creation, image-motion video rendering, analytics and publishing')
params=st.query_params
if params.get('code') and params.get('state'):
    try:
        redirect=os.getenv('AUTPOSTER_REDIRECT_URI') or st.secrets.get('AUTPOSTER_REDIRECT_URI')
        if not redirect: raise RuntimeError('AUTPOSTER_REDIRECT_URI is not configured')
        if st.session_state.get('oauth_state') != params.get('state'): raise RuntimeError('OAuth state mismatch')
        finish_authorization(redirect,str(params.get('code')),str(params.get('state'))); st.session_state['youtube_connected']=True; st.query_params.clear(); st.success('YouTube connected successfully.'); st.rerun()
    except Exception as e: st.error(f'YouTube authorization failed: {e}')

posts=list_posts(); video_count=len(list(RENDER_DIR.glob('*.mp4'))); queued=len([p for p in posts if p['status'] in ('queued','publishing')]); published=len([p for p in posts if p['status']=='published']); failed=len([p for p in posts if p['status']=='failed'])
c1,c2,c3,c4=st.columns(4); c1.metric('Videos',video_count); c2.metric('Queued',queued); c3.metric('Published',published); c4.metric('Failed',failed)

st.divider(); st.subheader('🎬 Create Video')
with st.form('create_video_next'):
    topic=st.text_input('Topic',placeholder='Why people stay broke after getting a raise')
    platforms=st.multiselect('Target platforms',PLATFORMS,default=['youtube'])
    video_type=st.selectbox('Video type',['Short-form','Long-form'])
    ratio=st.selectbox('Aspect ratio',list(SUPPORTED_ASPECT_RATIOS.keys()))
    duration=st.number_input('Duration (seconds)',10,7200,45 if video_type=='Short-form' else 660,10)
    style=st.selectbox('Video style',['Cinematic documentary','Realistic','3D','UGC','News','Educational','Dark documentary','Luxury','Anime'])
    script_mode=st.radio('Script',['Generate with AI','Paste my script'],horizontal=True)
    script_input=st.text_area('Script / narration',placeholder='Paste your script here' if script_mode=='Paste my script' else 'Leave empty to generate automatically')
    voice=st.selectbox('Voice',['Female','Male'])
    logo=st.file_uploader('Brand logo (optional)',type=['png','jpg','jpeg'])
    visual_mode=st.selectbox('Visual mode',['AI images + 3–5 sec motion','Simple audio render'])
    generate=st.form_submit_button('🚀 Generate Video')
if generate:
    try:
        if not topic.strip(): raise ValueError('Topic is required')
        script=script_input.strip() if script_mode=='Paste my script' else generate_script(topic,int(duration),style)
        project=create_project(topic,script,video_type.lower(),int(duration),topic,platforms=platforms); project.video_plan.aspect_ratio=ratio; project.video_plan.width,project.video_plan.height=SUPPORTED_ASPECT_RATIOS[ratio]; project.save()
        scenes=generate_scene_plan_ai(script,style)
        st.success(f'Script generated and {len(scenes)} scenes planned.')
        st.text_area('Generated narration',script,height=220)
        with st.expander('Scene plan'): st.json(scenes)
        safe=''.join(c if c.isalnum() else '_' for c in topic)[:55] or 'video'; audio=VIDEO_DIR/f'{safe}_voice.wav'; final=RENDER_DIR/f'{safe}_{ratio.replace(":","x")}.mp4'
        with st.spinner('Generating voiceover...'): generate_voiceover(script,str(audio))
        w,h=SUPPORTED_ASPECT_RATIOS[ratio]
        if visual_mode.startswith('AI images'):
            with st.spinner(f'Generating {len(scenes)} visual scenes and adding motion...'):
                render_from_scenes(scenes,str(audio),str(final),str(ASSET_DIR),str(CLIP_DIR),w,h)
        else:
            from video_factory import make_video
            make_video(str(audio),str(final),w,h)
        if logo:
            lp=ASSET_DIR/('brand_logo'+Path(logo.name).suffix); lp.write_bytes(logo.getbuffer()); branded=RENDER_DIR/f'{safe}_{ratio.replace(":","x")}_branded.mp4'; add_logo(str(final),str(lp),str(branded)); final=branded
        st.success('🎉 Video generated.'); st.video(str(final)); st.download_button('⬇️ Download MP4',final.read_bytes(),file_name=final.name,mime='video/mp4')
        st.subheader('Platform-specific metadata')
        for p in platforms:
            m=generate_metadata(topic,script,p); st.write(f'**{p.title()}** — {m.title}'); st.caption(m.caption); st.code(' '.join(m.tags))
    except Exception as e: st.error(f'Generation failed: {e}')

st.divider(); st.subheader('📤 Upload Existing Video')
upload=st.file_uploader('Upload MP4/MOV/M4V',type=['mp4','mov','m4v'])
if upload:
    destination=VIDEO_DIR/upload.name
    if not destination.exists(): destination.write_bytes(upload.getbuffer())
    with st.form('new_post_next'):
        ptitle=st.text_input('Title',Path(upload.name).stem); description=st.text_area('Description'); hashtags=st.text_input('Hashtags'); target=st.multiselect('Platforms',PLATFORMS,default=['youtube'])
        if st.form_submit_button('Add to publishing queue'):
            now=datetime.now(timezone.utc).isoformat(); add_post({'filename':upload.name,'title':ptitle,'description':description,'hashtags':hashtags,'platforms':target,'scheduled_at':None,'status':'queued','created_at':now,'updated_at':now}); st.success('Added to queue.'); st.rerun()

st.divider(); st.subheader('📊 Analytics')
try: connected=credentials() is not None
except Exception: connected=False
if connected:
    try:
        ch=channel_summary(); stats=ch.get('statistics',{}); a,b,c=st.columns(3); a.metric('Subscribers',stats.get('subscriberCount','0')); b.metric('Views',stats.get('viewCount','0')); c.metric('Videos',stats.get('videoCount','0'))
        if st.button('Refresh YouTube analytics'): st.json(analytics_report(28))
    except Exception as e: st.warning(str(e))
else: st.info('YouTube is not authorized yet.')

st.divider(); st.subheader('🚀 YouTube')
if connected: st.success('YouTube connected — private upload is available below.')
else:
    try: redirect=os.getenv('AUTPOSTER_REDIRECT_URI') or st.secrets.get('AUTPOSTER_REDIRECT_URI')
    except Exception: redirect=os.getenv('AUTPOSTER_REDIRECT_URI')
    if redirect and st.button('Connect YouTube'):
        url,state=authorization_url(redirect); st.session_state['oauth_state']=state; st.link_button('Continue to Google authorization',url)
    else: st.warning('Set AUTPOSTER_REDIRECT_URI first, then connect YouTube.')

st.subheader('Publishing queue')
for post in list_posts():
    with st.expander(f"#{post['id']} • {post['filename']} • {post['status']}"):
        st.write(f"Platforms: {post['platforms']} | Scheduled: {post['scheduled_at'] or 'Now'}")
        if connected and 'youtube' in post['platforms'] and st.button('Upload to YouTube (private)',key=f"yt_next_{post['id']}"):
            try:
                result=upload_video(str(VIDEO_DIR/post['filename']),post['title'],post.get('description','')+'\n'+post.get('hashtags',''),'private'); update_post(post['id'],status='published',platform_results=json.dumps({'youtube':result}),last_error=''); st.success(f"Uploaded privately: {result.get('id','')}"); st.rerun()
            except Exception as e: update_post(post['id'],status='failed',last_error=str(e)); st.error(str(e))

st.divider(); st.subheader('Platform status')
for n,s in {'YouTube':'🟢 OAuth/upload/analytics','Instagram':'🟡 Meta API authorization required','Facebook':'🟡 Meta API authorization required','TikTok':'🟡 TikTok API approval/authorization required','LinkedIn':'🟡 LinkedIn API authorization required'}.items(): st.write(f'**{n}:** {s}')
st.caption('Official APIs only. Never put social passwords or API tokens in source code.')
