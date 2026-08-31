"""Minimal GPU worker for a free CUDA notebook runtime.
Run on Kaggle/Colab with this repository mounted or cloned.
The worker exposes local functions that can be called by a thin HTTP/Gradio
wrapper later; keeping model code here makes the provider replaceable.
"""
from generation_engine import generate_image, generate_video, image_engine_status, video_engine_status

if __name__ == "__main__":
    print("Image engine:", image_engine_status())
    print("Video engine:", video_engine_status())
    print("Set FLUX_MODEL_PATH/WAN_MODEL_PATH only if using local model directories.")
    print("Default model IDs are resolved by Diffusers from Hugging Face.")
