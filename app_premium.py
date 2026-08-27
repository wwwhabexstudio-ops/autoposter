from __future__ import annotations
from pathlib import Path
import os, streamlit as st
from database import list_posts, update_post
from backend import build_video, queue_video, generate_script, generate_metadata, RENDER_DIR, VIDEO_DIR
from caption_renderer import make_srt, burn_captions
from youtube_adapter import authorization_url, finish_authorization, credentials, upload_video
from youtube_analytics import channel_summary, analytics_report

st.set_page_config(page_title='AutoPoster Studio',page_icon='✦',layout='wide',initial_sidebar_state='expanded')
if 'logged_in' not in st.session_state: st.session_state.logged_in=False
if not st.session_state.logged_in:
    st.markdown('# ✦ AutoPoster Studio'); st.caption('Create • Publish • Analyze • Improve')
    email=st.text_input('Email address',placeholder='you@example.com')
    if st.button('Continue to Studio',type='primary',use_container_width=True):
        if '@' in email and '.' in email.rsplit('@',1)[-1]: st.session_state.logged_in=True; st.session_state.user_email=email; st.rerun()
        else: st.error('Enter a valid email address.')
    st.info('Sign in is required before entering the studio.'); st.stop()

params=st.query_params
if params.get('code') and params.get('state'):
    try:
        redirect=os.getenv('AUTPOSTER_REDIRECT_URI') or st.secrets.get('AUTPOSTER_REDIRECT_URI')
        if not redirect: raise RuntimeError('AUTPOSTER_REDIRECT_URI is not configured')
        if st.session_state.get('oauth_state') != params.get('state'): raise RuntimeError('OAuth state mismatch')
        finish_authorization(redirect,str(params.get('code')),str(params.get('state'))); st.query_params.clear(); st.success('YouTube connected.'); st.rerun()
    except Exception as e: st.error(f'YouTube authorization failed: {e}')

st.sidebar.markdown('# ✦ AutoPoster'); st.sidebar.caption(st.session_state.get('user_email',''))
page=st.sidebar.radio('Workspace',['Dashboard','Create','Upload','Publish','Analytics','AI Insights','Content Library','Settings'])
try: yt_connected=credentials() is not None
except Exception: yt_connected=False

if page=='Dashboard':
    posts=list_posts(); files=list(RENDER_DIR.glob('*.mp4')); st.title('Content command center')
    a,b,c,d=st.columns(4); a.metric('Videos',len(files)); b.metric('Queued',sum(p['status']=='queued' for p in posts)); c.metric('Published',sum(p['status']=='published' for p in posts)); d.metric('Failed',sum(p['status']=='failed' for p in posts))
    st.markdown('### Connected accounts'); st.success('YouTube connected' if yt_connected else 'YouTube not connected'); st.caption('Other platforms require their official OAuth/API authorization.')

elif page=='Create':
    st.title('Create video'); st.caption('Destination → topic → script → production → generate')
    st.subheader('1 · Destination accounts')
    destinations=st.multiselect('Platforms',['YouTube','Instagram','TikTok','Facebook','LinkedIn'],default=['YouTube'])
    if 'YouTube' in destinations:
        if yt_connected: st.selectbox('YouTube channel',['Connected YouTube channel'])
        else: st.warning('YouTube is not connected yet. You can generate first and connect before publishing.')
    for p in destinations:
        if p!='YouTube': st.selectbox(f'{p} account',['Connect account — required'],key='acct_'+p)

    st.subheader('2 · Topic & script')
    topic=st.text_input('Topic',placeholder='Why people stay broke after getting a raise')
    a,b=st.columns(2); duration=a.number_input('Duration (seconds)',10,7200,660,10); video_type=b.selectbox('Video type',['Long-form','Short-form'])
    script_mode=st.radio('Script',['Generate with AI','Paste my script'],horizontal=True)
    if script_mode=='Generate with AI':
        if st.button('✨ Generate Script',use_container_width=True):
            if not topic.strip(): st.error('Enter a topic first.')
            else:
                with st.spinner('Writing script...'): st.session_state.generated_script=generate_script(topic,int(duration),'cinematic documentary')
        script=st.text_area('Script / narration',value=st.session_state.get('generated_script',''),height=260)
    else: script=st.text_area('Script / narration',height=260)

    st.subheader('3 · Production settings')
    a,b,c=st.columns(3); ratio=a.selectbox('Aspect ratio',['16:9','9:16','1:1']); style=b.selectbox('Visual style',['Cinematic documentary','Realistic','3D','UGC','News','Educational','Dark documentary','Luxury','Anime']); visual=c.selectbox('Visual mode',['AI Images + 3–5 sec motion','AI Motion Video','Audio only'])
    a,b,c=st.columns(3); voice=a.selectbox('Voice',['Female','Male']); caption=b.selectbox('Caption text style',['Bold','Minimal','Boxed','Karaoke','None']); music=c.checkbox('Automatically match background music',True)
    logo=st.file_uploader('Brand logo (optional)',type=['png','jpg','jpeg'])

    if st.button('🚀 Generate Video',type='primary',use_container_width=True):
        try:
            if not topic.strip(): raise ValueError('Topic is required.')
            if not script.strip():
                with st.spinner('Generating script automatically...'): script=generate_script(topic,int(duration),style); st.session_state.generated_script=script
            with st.spinner('Creating scenes, visuals, voiceover and video...'):
                final,scenes=build_video(topic,script,int(duration),video_type,ratio,style,voice,visual,logo)
            if caption!='None':
                srt=VIDEO_DIR/(Path(final).stem+'.srt'); make_srt(script,str(srt)); captioned=RENDER_DIR/(Path(final).stem+'_captions.mp4'); burn_captions(str(final),str(srt),str(captioned),caption); final=captioned
            st.session_state.last_video=str(final); st.session_state.last_script=script; st.session_state.last_topic=topic; st.session_state.last_platforms=destinations
            st.success('🎉 Video generated successfully.'); st.video(str(final)); st.download_button('⬇️ Download MP4',Path(final).read_bytes(),file_name=Path(final).name,mime='video/mp4')
            st.markdown('### 🚀 Publish this video')
            if st.button('📤 Add to Publish Queue',type='primary'):
                first=generate_metadata(topic,script,(destinations[0] if destinations else 'YouTube').lower()); queue_video(final,first.title,first.caption,' '.join(first.tags),[p.lower() for p in destinations] or ['youtube']); st.success('Added to publishing queue. Open Publish to review and publish.')
        except Exception as e: st.error(f'Generation failed: {e}')

elif page=='Upload':
    st.title('Upload existing video'); upload=st.file_uploader('MP4 / MOV / M4V',type=['mp4','mov','m4v'])
    if upload:
        target=VIDEO_DIR/upload.name; target.write_bytes(upload.getbuffer()); st.video(upload); title=st.text_input('Title',Path(upload.name).stem); desc=st.text_area('Description'); tags=st.text_input('Hashtags'); plats=st.multiselect('Publish to',['youtube','instagram','tiktok','facebook','linkedin'],['youtube'])
        if st.button('Add to publishing queue',type='primary'): queue_video(target,title,desc,tags,plats); st.success('Queued.')

elif page=='Publish':
    st.title('Publish'); st.subheader('1 · Choose destination account')
    if yt_connected: st.selectbox('YouTube account',['Connected YouTube channel'])
    else:
        st.warning('YouTube requires OAuth authorization.')
        try: redirect=os.getenv('AUTPOSTER_REDIRECT_URI') or st.secrets.get('AUTPOSTER_REDIRECT_URI')
        except Exception: redirect=os.getenv('AUTPOSTER_REDIRECT_URI')
        if redirect and st.button('Connect YouTube'):
            url,state=authorization_url(redirect); st.session_state.oauth_state=state; st.link_button('Continue to Google authorization',url)
    st.subheader('2 · Publishing queue')
    for post in list_posts():
        with st.container(border=True):
            st.write(f"**{post['filename']}** · {post['status']} · {post['platforms']}")
            if yt_connected and 'youtube' in post['platforms'] and st.button('🚀 Publish to selected YouTube channel',key=f'pub{post["id"]}'):
                try:
                    result=upload_video(str(VIDEO_DIR/post['filename']),post['title'],post.get('description','')+'\n'+post.get('hashtags',''),'private'); update_post(post['id'],status='published',platform_results=str({'youtube':result}),last_error=''); st.success(f"Uploaded privately. Video ID: {result.get('id','')}"); st.rerun()
                except Exception as e: st.error(f'YouTube upload failed: {e}')

elif page=='Analytics':
    st.title('Analytics')
    if yt_connected:
        try:
            stats=channel_summary().get('statistics',{}); a,b,c=st.columns(3); a.metric('Subscribers',stats.get('subscriberCount','0')); b.metric('Views',stats.get('viewCount','0')); c.metric('Videos',stats.get('videoCount','0'))
            if st.button('Refresh YouTube analytics'): st.json(analytics_report(28))
        except Exception as e: st.error(str(e))
    else: st.info('Connect YouTube to load live analytics.')

elif page=='AI Insights': st.title('AI Insights'); st.info('Performance patterns and next-video recommendations will improve as platform data accumulates.')
elif page=='Content Library':
    st.title('Content Library')
    for f in sorted(RENDER_DIR.glob('*.mp4'),reverse=True):
        with st.container(border=True): st.write(f.name); st.download_button('Download',f.read_bytes(),file_name=f.name,mime='video/mp4',key='dl_'+f.name)
elif page=='Settings': st.title('Settings'); st.write('Signed in as:',st.session_state.get('user_email','')); st.caption('Keep API keys and OAuth secrets in Codespaces secrets.')
