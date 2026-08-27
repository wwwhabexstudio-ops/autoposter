# Real voice + generation runtime

The app must not claim a production video is ready when it has only placeholder visuals or robotic fallback audio.

## Voice
Use a neural TTS backend (Piper or another configured neural provider). Store model paths/configuration in environment variables/Codespaces secrets. eSpeak is development fallback only and should not be used for production voice.

## Images
FLUX.1-schnell is the local image-model target. Set `FLUX_MODEL_PATH` and run the image worker on a compatible CUDA GPU.

## Video
Wan2.1 T2V-1.3B is the local video-model target. Set `WAN_MODEL_PATH` and run the video worker on a compatible CUDA GPU.

## Important
GitHub Codespaces CPU compute cannot be turned into a CUDA GPU by software. The repository contains the integration boundaries, but actual model inference requires a compatible runtime and model weights. Do not silently substitute colored placeholders for production generation.
