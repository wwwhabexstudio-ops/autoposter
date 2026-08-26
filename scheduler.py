from __future__ import annotations

import time
from datetime import datetime, timezone

from worker import run_once


if __name__ == "__main__":
    print("AutoPoster scheduler started. Checking every 60 seconds.")
    while True:
        try:
            print(f"[{datetime.now(timezone.utc).isoformat()}] checking queue")
            run_once()
        except Exception as exc:
            print(f"Worker error: {exc}")
        time.sleep(60)
