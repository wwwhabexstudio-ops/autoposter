"""YouTube OAuth and upload adapter.

Credentials are loaded from environment variables or Streamlit secrets; never
commit client secrets to the repository.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/yt-analytics.readonly"]
TOKEN_FILE = Path("data/youtube_token.json")


def _client_config() -> dict[str, Any]:
    import json
    raw = os.getenv("GOOGLE_OAUTH_CLIENT_JSON")
    if not raw:
        raise RuntimeError("GOOGLE_OAUTH_CLIENT_JSON is not configured")
    return json.loads(raw)


def authorization_url(redirect_uri: str) -> tuple[str, str]:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, redirect_uri=redirect_uri)
    url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    return url, state


def finish_authorization(redirect_uri: str, authorization_response: str, state: str) -> Credentials:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=state, redirect_uri=redirect_uri)
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def credentials() -> Credentials:
    if not TOKEN_FILE.exists():
        raise RuntimeError("YouTube is not connected yet")
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def service():
    return build("youtube", "v3", credentials=credentials())


def upload_video(path: str, title: str, description: str = "", privacy: str = "private") -> dict[str, Any]:
    body = {"snippet": {"title": title, "description": description}, "status": {"privacyStatus": privacy}}
    request = service().videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(path, chunksize=-1, resumable=True))
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response
