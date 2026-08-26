from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .base import PlatformAdapter, PublishResult

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = Path(os.getenv("YOUTUBE_TOKEN_FILE", "data/youtube_token.json"))
CLIENT_FILE = Path(os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json"))


class YouTubeAdapter(PlatformAdapter):
    name = "youtube"

    def _credentials(self) -> Credentials:
        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        if not creds or not creds.valid:
            if not CLIENT_FILE.exists():
                raise FileNotFoundError(
                    f"Missing {CLIENT_FILE}. Create OAuth Desktop credentials in Google Cloud and place the JSON file there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def publish(self, video_path: Path, title: str, description: str, hashtags: str) -> PublishResult:
        try:
            youtube = build("youtube", "v3", credentials=self._credentials())
            clean_tags = [tag.strip().lstrip("#") for tag in hashtags.split() if tag.strip()]
            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": clean_tags,
                    "categoryId": "22",
                },
                "status": {"privacyStatus": os.getenv("YOUTUBE_PRIVACY", "private")},
            }
            media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            while response is None:
                _, response = request.next_chunk()
            video_id = response["id"]
            return PublishResult(True, self.name, video_id, f"https://www.youtube.com/watch?v={video_id}")
        except Exception as exc:
            return PublishResult(False, self.name, error=str(exc))
