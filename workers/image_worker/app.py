import os
import torch
import gradio as gr
from diffusers import FluxPipeline

MODEL=os.getenv('FLUX_MODEL','black-forest-labs/FLUX.1-schnell')
pipe=None

def generate(prompt, width=1024, height=576, steps=4):
    global pipe
    if not torch.cuda.is_available(): raise RuntimeError('CUDA GPU required')
    if pipe is None:
        pipe=FluxPipeline.from_pretrained(MODEL, torch_dtype=torch.bfloat16)
        pipe.enable_model_cpu_offload()
    result=pipe(prompt=prompt, height=int(height), width=int(width), num_inference_steps=int(steps), guidance_scale=0.0).images[0]
    return result

with gr.Blocks(title='AutoPoster Image Engine') as demo:
    gr.Markdown('# AutoPoster Real AI Image Engine')
    p=gr.Textbox(label='Scene prompt')
    w=gr.Number(value=1024,label='Width')
    h=gr.Number(value=576,label='Height')
    s=gr.Slider(1,8,value=4,step=1,label='Steps')
    out=gr.Image(type='pil',label='Generated image')
    gr.Button('Generate').click(generate,[p,w,h,s],out)

demo.queue().launch()
