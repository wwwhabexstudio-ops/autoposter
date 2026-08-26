"""Google/YouTube OAuth helpers.

Credentials are read from environment variables. No secrets belong in source control.
"""

from __future__ import annotations

import os
from urllib.parse import urlencode

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def authorization_url(state: str) -> str:
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"
