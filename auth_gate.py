"""Simple email login gate for the private AutoPoster workspace."""
from __future__ import annotations
import os, re, streamlit as st

def require_login() -> bool:
    if st.session_state.get('autoposter_user'): return True
    st.title('Welcome to AutoPoster')
    st.caption('Sign in to create and publish content.')
    with st.form('login'):
        email=st.text_input('Email address',placeholder='you@example.com')
        if st.form_submit_button('Continue'):
            if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email.strip()): st.error('Enter a valid email address.')
            else:
                allowed=os.getenv('AUTOPOSTER_ALLOWED_EMAILS','').strip()
                if allowed and email.lower() not in {x.strip().lower() for x in allowed.split(',')}: st.error('This email is not authorized for this workspace.')
                else: st.session_state['autoposter_user']=email.strip().lower(); st.rerun()
    return False

def logout():
    st.session_state.pop('autoposter_user',None); st.rerun()
