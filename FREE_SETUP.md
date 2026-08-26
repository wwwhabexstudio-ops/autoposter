# AutoPoster free setup

## 1. AI scripts
Create a Gemini API key in Google AI Studio and store it as the Codespace environment secret `GEMINI_API_KEY`. The current Gemini API has a free tier with model/rate limits; it is not unlimited.

Optional: set `GEMINI_MODEL` (default `gemini-3.7-flash`).

## 2. YouTube
Store these as secrets/environment variables, never in Git:
- `GOOGLE_OAUTH_CLIENT_JSON`
- `AUTPOSTER_REDIRECT_URI`

Use the exact HTTPS callback URL exposed by the deployed app and register the same URI in the Google OAuth client.

## 3. Real AI motion video
The main Codespace is not assumed to have a CUDA GPU. Run `gpu_worker/server.py` on a CUDA-capable machine/session:

```bash
pip install -r gpu_worker/requirements.txt
uvicorn gpu_worker.server:app --host 0.0.0.0 --port 7860
```

Then set `MOTION_WORKER_URL` in AutoPoster to the worker's HTTPS URL.

The worker uses the open-source Wan2.1 T2V 1.3B Diffusers model. It produces short motion clips; AutoPoster is designed to concatenate many clips into long-form videos.

## 4. What cannot be automated
The app cannot grant itself access to your Google/Meta/TikTok/LinkedIn accounts, create private credentials without your authorization, or create GPU compute where none exists. Those account authorization/approval steps must be done by the account owner. Everything else can be automated in code.
