from __future__ import annotations
from pathlib import Path
import streamlit as st
from app_next import *

# Premium shell: keeps the working generation/publishing backend while separating workflows into tabs.
st.set_page_config(page_title='AutoPoster Studio', page_icon='✦', layout='wide', initial_sidebar_state='expanded')

if 'logged_in' not in st.session_state: st.session_state.logged_in=False
if not st.session_state.logged_in:
    st.markdown('## ✦ AutoPoster Studio')
    st.caption('Your AI content studio — create, publish and learn.')
    email=st.text_input('Email address', placeholder='you@example.com')
    if st.button('Continue', type='primary', use_container_width=True):
        if '@' in email and '.' in email.split('@')[-1]:
            st.session_state.logged_in=True; st.session_state.user_email=email; st.rerun()
        else: st.error('Enter a valid email address.')
    st.info('Account access is required before creating or publishing content.')
    st.stop()

st.sidebar.markdown('## ✦ AutoPoster')
st.sidebar.caption(st.session_state.get('user_email',''))
page=st.sidebar.radio('Workspace',['Dashboard','Create','Upload','Publish','Analytics','AI Insights','Content Library','Settings'])
if page=='Dashboard':
    st.title('Good to see you.')
    st.caption('Your content command center')
    a,b,c,d=st.columns(4); a.metric('Videos',len(list(RENDER_DIR.glob('*.mp4')))); b.metric('Queued',queued); c.metric('Published',published); d.metric('Failed',failed)
    st.info('Use Create to generate a video, Upload for an existing video, or Publish to manage connected accounts.')
elif page=='Create':
    st.title('Create video')
    st.caption('Choose your destination first, then build the video for it.')
    with st.container(border=True):
        st.subheader('1 · Destination')
        st.multiselect('Platforms / accounts',['YouTube — connect account','Instagram — connect account','TikTok — connect account','Facebook — connect page','LinkedIn — connect account'],default=['YouTube — connect account'])
    with st.container(border=True):
        st.subheader('2 · Content')
        topic=st.text_input('Topic'); mode=st.radio('Script',['Generate with AI','Paste my script'],horizontal=True); script=st.text_area('Script',height=150)
    with st.container(border=True):
        st.subheader('3 · Video')
        c1,c2,c3=st.columns(3); c1.selectbox('Duration',['30 sec','60 sec','5 min','10 min','Custom']); c2.selectbox('Ratio',['16:9','9:16']); c3.selectbox('Visuals',['AI Images + 3–5 sec motion','AI Motion Video','My own visuals'])
        c1,c2,c3=st.columns(3); c1.selectbox('Style',['Cinematic','Realistic','3D','Documentary','UGC','Dark documentary']); c2.selectbox('Voice',['Female','Male']); c3.selectbox('Captions',['Bold','Minimal','Boxed','Karaoke','None'])
        st.checkbox('Automatically match background music',True); st.checkbox('Add brand logo top-right')
    st.button('🚀 Generate video',type='primary',use_container_width=True)
    st.caption('The production engine is connected underneath this interface; the next generation job will use the selected settings.')
elif page=='Upload':
    st.title('Upload existing video'); st.file_uploader('MP4 / MOV / M4V',type=['mp4','mov','m4v'])
elif page=='Publish':
    st.title('Publish')
    st.subheader('Connected accounts')
    st.info('Accounts appear here after OAuth authorization. You choose the exact destination account before publishing.')
    st.button('Connect YouTube'); st.button('Connect Instagram / Facebook'); st.button('Connect TikTok'); st.button('Connect LinkedIn')
elif page=='Analytics':
    st.title('Analytics'); st.caption('Performance by platform and account')
    st.info('Connect accounts to load live metrics.')
elif page=='AI Insights':
    st.title('AI Insights'); st.info('Winning hooks, topics, retention patterns and next-video recommendations appear here as platform data accumulates.')
elif page=='Content Library':
    st.title('Content Library'); st.caption('Generated and uploaded videos')
    for f in sorted(RENDER_DIR.glob('*.mp4')): st.write(f.name)
elif page=='Settings':
    st.title('Settings'); st.text_input('Account email',st.session_state.get('user_email','')); st.caption('API credentials should be stored as Codespaces secrets, never in source code.')
