"""OAuth configuration helpers for AutoPoster.

Secrets are read from environment variables and are never stored in the repo.
"""

import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def google_configured() -> bool:
    return all((GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI))
