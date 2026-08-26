"""Connected-account registry for the publishing UI.
Secrets/tokens are intentionally not stored here; platform adapters own OAuth.
"""
from __future__ import annotations
import streamlit as st

def account_selector(platforms: list[str]) -> dict[str,str]:
    selected={}
    st.subheader('👤 Choose destination accounts')
    for p in platforms:
        key=f'account_{p}'
        if p == 'youtube':
            try:
                from youtube_adapter import credentials
                connected=credentials() is not None
            except Exception: connected=False
            if connected:
                try:
                    from youtube_analytics import channel_summary
                    ch=channel_summary(); name=ch.get('snippet',{}).get('title') or ch.get('id','Connected YouTube channel')
                except Exception: name='Connected YouTube channel'
                selected[p]=st.selectbox('YouTube account',[name],key=key)
            else:
                st.warning('YouTube: connect an account below before publishing.')
        else:
            st.selectbox(p.title()+' account',['Connect '+p.title()+' account first'],key=key,disabled=True)
    return selected
