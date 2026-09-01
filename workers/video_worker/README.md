# AutoPoster free GPU video worker

This worker is designed for a free Google Colab T4. It runs **Wan2.1 T2V 1.3B** and exposes `/health`, `/generate`, and `/download/{job_id}`.

## Colab

```bash
pip install -U -r workers/video_worker/requirements.txt fastapi uvicorn
python workers/video_worker/gpu_worker.py
```

The worker must run on the CUDA runtime, not on the Streamlit/Codespace server. For the first test, generate a 3–5 second clip. A 30-second video should be assembled from multiple short scenes rather than one huge generation.

## Connect AutoPoster

Set these environment variables on the Streamlit app:

```text
GPU_WORKER_URL=https://your-public-worker-url
GPU_WORKER_TOKEN=your-random-token
```

Set the same `GPU_WORKER_TOKEN` in Colab. Do not commit tokens or API keys.

The worker uses CPU offload so it can target a 14–16 GB consumer GPU. Generation speed depends on the current Colab T4 allocation and model load time.
