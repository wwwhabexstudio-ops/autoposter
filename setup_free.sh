#!/usr/bin/env bash
set -e
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ffmpeg espeak-ng
fi
python -m pip install -r requirements.txt
printf '\nAutoPoster free dependencies installed.\n'
