from __future__ import annotations
import streamlit as st
from platform_intelligence import generate_metadata, analyze

def render_intelligence():
    st.divider(); st.subheader('🧠 Content Intelligence')
    topic=st.text_input('Topic for platform optimization', key='intel_topic')
    script=st.text_area('Script for optimization', key='intel_script')
    platform=st.selectbox('Platform', ['youtube','tiktok','instagram','facebook','linkedin'], key='intel_platform')
    if st.button('Generate platform-optimized metadata'):
        if not topic.strip() or not script.strip(): st.error('Enter a topic and script.')
        else:
            r=generate_metadata(topic,script,platform)
            st.write('**Recommended hook:**',r.hook)
            st.write('**Title:**',r.title)
            st.write('**Caption:**',r.caption)
            st.write('**Tags:**',' '.join(r.tags))
    st.caption('Performance learning becomes stronger as platform analytics are connected.')
