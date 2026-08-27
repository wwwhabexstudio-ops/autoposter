# GPU generation workers

This directory is the runtime boundary for real model inference. The main AutoPoster app remains unchanged.

## Image worker
Run a Hugging Face ZeroGPU Space using the FLUX Diffusers pipeline. Expose a Gradio API endpoint accepting `prompt`, `width`, `height`, and returning a generated PNG.

## Video worker
Run a Hugging Face ZeroGPU Space using Wan2.1 T2V-1.3B (or a compatible open video model) through Diffusers. Expose a Gradio API accepting `prompt`, `seconds`, `width`, `height`, returning an MP4.

## Client contract
The app should call workers asynchronously and poll job status. Never report a generation as complete until the returned PNG/MP4 exists and is readable.

Environment variables in Codespaces/production secrets:
- HF_TOKEN
- IMAGE_WORKER_URL
- VIDEO_WORKER_URL

Free ZeroGPU has limited daily GPU quota. For long videos, generate short scenes and assemble them locally; do not attempt one huge inference job.
