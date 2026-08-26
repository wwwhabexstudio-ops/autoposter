# AutoPoster Motion Worker

This is an optional GPU worker for true AI motion clips. It is intentionally separate from the Streamlit app because Codespaces commonly has no GPU.

## Intended flow
1. AutoPoster writes a scene job JSON.
2. A GPU host runs `wan_worker.py`.
3. The worker generates short clips per scene.
4. Clips are returned to `data/motion_jobs/<job_id>/clips/`.
5. AutoPoster assembles them with narration, music, captions and branding.

The worker is model-agnostic at the API boundary. Set `MODEL_BACKEND=wan2.1` on a GPU host and install the model-specific dependencies there. No paid API is required by this interface.

The first supported backend is a local Diffusers/Wan2.1-style worker. Actual inference requires a compatible NVIDIA GPU and model weights; this cannot be created by Streamlit/FFmpeg alone.
