"""Final video factory: real Wan2.1 moving scenes synchronized to narration."""
from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path
from motion_worker import generate_motion_clip


def _run(cmd:list[str])->None:
    subprocess.run(cmd,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)


def _probe(path:str)->float:
    ffprobe=shutil.which("ffprobe")
    if not ffprobe: raise RuntimeError("FFprobe is required")
    r=subprocess.run([ffprobe,"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",path],check=True,capture_output=True,text=True)
    return max(.1,float(r.stdout.strip()))


def _split_words(text:str,count:int)->list[str]:
    words=text.split(); count=max(1,min(count,len(words)))
    result=[]; start=0
    for i in range(count):
        end=round((i+1)*len(words)/count); result.append(" ".join(words[start:end])); start=end
    return [x for x in result if x]


def _prepare_scenes(raw:list[dict],seconds:float,topic:str)->list[dict]:
    count=max(1,round(seconds/4))
    narration=" ".join(str(x.get("narration") or "") for x in raw).strip() or topic
    chunks=_split_words(narration,count)
    raw_prompts=[str(x.get("visual_prompt") or "") for x in raw]
    prompts=raw_prompts if len(raw_prompts)==len(chunks) and all(raw_prompts) else [f"cinematic realistic documentary moving shot, physically observable action directly visualizing: {chunk}; no text, no subtitles, no typography, no title card, no infographic, no presentation slide, no UI" for chunk in chunks]
    return [{"scene":i+1,"narration":chunks[i],"visual_prompt":prompts[i] + "; real moving video, natural motion, cinematic camera movement, visually distinct from other scenes, no readable text" ,"duration_seconds":seconds/len(chunks)} for i in range(len(chunks))]


def _normalize(source:Path,out:Path,width:int,height:int,seconds:float)->None:
    ffmpeg=shutil.which("ffmpeg")
    vf=f"scale={width*12//10}:{height*12//10}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,format=yuv420p"
    _run([ffmpeg,"-y","-i",str(source),"-t",f"{seconds:.3f}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-r","15",str(out)])


def _concat(clips:list[Path],out:Path)->None:
    ffmpeg=shutil.which("ffmpeg"); txt=out.with_suffix(".txt")
    txt.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips),encoding="utf-8")
    try:_run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-an",str(out)])
    finally:txt.unlink(missing_ok=True)


def make_video(audio:str,output:str,width:int,height:int,duration:float|None=None,image:str|None=None,scenes:list[dict]|None=None,topic:str="AutoPoster")->str:
    if not shutil.which("ffmpeg"): raise RuntimeError("FFmpeg is not installed")
    if not Path(audio).exists(): raise RuntimeError(f"Narration audio not found: {audio}")
    # Wan2.1 is mandatory. There is intentionally no static/image/text-card fallback.
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True)
    seconds=float(duration or _probe(audio)); selected=_prepare_scenes(scenes or [],seconds,topic)
    work=out.parent/f".{out.stem}_wan_scenes"; work.mkdir(parents=True,exist_ok=True); clips=[]
    try:
        for i,scene in enumerate(selected,1):
            clip=work/f"scene_{i:02d}.mp4"; generated=work/f"wan_{i:02d}.mp4"
            generate_motion_clip(str(scene["visual_prompt"]),str(generated),width=width,height=height,seconds=max(1,round(scene["duration_seconds"])))
            _normalize(generated,clip,width,height,float(scene["duration_seconds"])); clips.append(clip)
        silent=work/"silent.mp4"; _concat(clips,silent)
        ffmpeg=shutil.which("ffmpeg")
        _run([ffmpeg,"-y","-i",str(silent),"-i",audio,"-t",f"{seconds:.3f}","-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(out)])
    finally:shutil.rmtree(work,ignore_errors=True)
    return str(out)
