import os
import torch
import gradio as gr
from diffusers import DiffusionPipeline

MODEL=os.getenv('VIDEO_MODEL','Wan-AI/Wan2.1-T2V-1.3B-Diffusers')
pipe=None

def generate(prompt, frames=81, width=832, height=480):
    global pipe
    if not torch.cuda.is_available(): raise RuntimeError('CUDA GPU required')
    if pipe is None:
        pipe=DiffusionPipeline.from_pretrained(MODEL, torch_dtype=torch.bfloat16)
        pipe.to('cuda')
    result=pipe(prompt=prompt, num_frames=int(frames), width=int(width), height=int(height)).frames[0]
    return result

with gr.Blocks(title='AutoPoster Video Engine') as demo:
    gr.Markdown('# AutoPoster Real AI Video Engine')
    p=gr.Textbox(label='Scene prompt')
    f=gr.Number(value=81,label='Frames')
    w=gr.Number(value=832,label='Width')
    h=gr.Number(value=480,label='Height')
    out=gr.Video(label='Generated video')
    gr.Button('Generate').click(generate,[p,f,w,h],out)

demo.queue().launch()
