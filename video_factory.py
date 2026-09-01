"""Finished-video factory with Wan2.1 motion-worker support."""
from __future__ import annotations
import hashlib, os, re, shutil, subprocess
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont
from motion_worker import generate_motion_clip


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _duration(audio: str) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe: raise RuntimeError("FFprobe is required for scene timing")
    r = subprocess.run([ffprobe,"-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",audio],check=True,capture_output=True,text=True)
    return max(.1,float(r.stdout.strip()))


def _safe_query(text: str) -> str:
    words=re.findall(r"[A-Za-z0-9]+",text.lower())
    stop={"the","and","that","this","with","from","they","their","about","what","when","your","into","have","people","there","will","just"}
    return " ".join(w for w in words if w not in stop and len(w)>3)[:90] or "cinematic documentary"


def _pexels_image(query: str, orientation: str, destination: Path) -> Path | None:
    key=os.getenv("PEXELS_API_KEY")
    if not key: return None
    try:
        r=requests.get("https://api.pexels.com/v1/search",headers={"Authorization":key},params={"query":query,"per_page":1,"orientation":orientation},timeout=20)
        r.raise_for_status(); photos=r.json().get("photos",[])
        if not photos:return None
        src=photos[0].get("src",{}); url=src.get("large2x") or src.get("large") or src.get("medium")
        if not url:return None
        data=requests.get(url,timeout=30); data.raise_for_status(); destination.write_bytes(data.content); return destination
    except Exception:return None


def _font(size:int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(p).exists():return ImageFont.truetype(p,size=size)
    return ImageFont.load_default()


def _make_fallback_card(text:str,topic:str,width:int,height:int,path:Path,index:int)->Path:
    digest=hashlib.md5(f"{topic}-{index}".encode()).hexdigest(); base=tuple(35+int(digest[i:i+2],16)%90 for i in (0,2,4))
    img=Image.new("RGB",(width,height),base); draw=ImageDraw.Draw(img,"RGBA")
    for n in range(6):
        x=int((n+1)*width/7); y=int(int(digest[(n*2)%24:(n*2)%24+2],16)/255*height); radius=max(50,min(width,height)//5)
        draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=(255,255,255,25),outline=(255,255,255,45),width=4)
    draw.rounded_rectangle((int(width*.08),int(height*.13),int(width*.92),int(height*.87)),radius=32,fill=(0,0,0,95),outline=(255,255,255,55),width=3)
    draw.text((int(width*.12),int(height*.19)),f"SCENE {index:02d}",font=_font(max(22,min(width,height)//25)),fill=(255,255,255,190))
    y=int(height*.34)
    for line in _wrap(text,29 if height>width else 48):
        draw.text((int(width*.12),y),line,font=_font(max(32,min(width,height)//13)),fill=(255,255,255,255)); y+=max(42,min(width,height)//12)
    img.save(path,quality=92); return path


def _wrap(text:str,width:int)->list[str]:
    words=text.split(); lines=[]; line=""
    for word in words:
        c=(line+" "+word).strip()
        if len(c)>width and line: lines.append(line); line=word
        else: line=c
    if line:lines.append(line)
    return lines[:7]


def _normalize_scenes(raw:list[dict],count:int,topic:str)->list[dict]:
    text=" ".join(str(s.get("narration") or "") for s in raw).strip() or topic
    words=text.split(); count=max(1,min(count,len(words))); base,extra=divmod(len(words),count); result=[]; cursor=0
    for i in range(count):
        take=base+(1 if i<extra else 0); chunk=" ".join(words[cursor:cursor+take]); cursor+=take
        result.append({"scene":i+1,"narration":chunk,"visual_prompt":f"cinematic realistic documentary moving shot illustrating: {chunk[:260]}"})
    return result


def _normalize_video(source:Path,output:Path,width:int,height:int,seconds:float)->None:
    ffmpeg=shutil.which("ffmpeg")
    vf=f"scale={width*12//10}:{height*12//10}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1,format=yuv420p"
    _run([ffmpeg,"-y","-i",str(source),"-t",f"{seconds:.3f}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-r","15",str(output)])


def _make_image_clip(image:Path,output:Path,width:int,height:int,seconds:float,index:int)->None:
    ffmpeg=shutil.which("ffmpeg"); frames=max(1,round(seconds*30)); zoom="min(zoom+0.0007,1.08)" if index%2 else "max(zoom-0.0005,1.0)"
    vf=f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps=30,format=yuv420p"
    _run([ffmpeg,"-y","-loop","1","-i",str(image),"-t",f"{seconds:.3f}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(output)])


def _concat(clips:list[Path],output:Path)->None:
    ffmpeg=shutil.which("ffmpeg"); txt=output.with_suffix(".txt")
    txt.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips),encoding="utf-8")
    try:_run([ffmpeg,"-y","-f","concat","-safe","0","-i",str(txt),"-c","copy","-an",str(output)])
    finally:txt.unlink(missing_ok=True)


def make_video(audio:str,output:str,width:int,height:int,duration:float|None=None,image:str|None=None,scenes:list[dict]|None=None,topic:str="AutoPoster")->str:
    if not shutil.which("ffmpeg"):raise RuntimeError("FFmpeg is not installed on the host")
    if not Path(audio).exists():raise RuntimeError(f"Narration audio not found: {audio}")
    out=Path(output); out.parent.mkdir(parents=True,exist_ok=True); work=out.parent/f".{out.stem}_scenes"; work.mkdir(parents=True,exist_ok=True)
    audio_seconds=float(duration or _duration(audio)); raw=scenes or [{"scene":1,"narration":topic}]; selected=_normalize_scenes(raw,max(1,round(audio_seconds/4)),topic)
    per_scene=audio_seconds/len(selected)
    clips=[]; worker_enabled=bool(os.getenv("MOTION_WORKER_URL"))
    orientation="portrait" if height>width else ("square" if height==width else "landscape")
    try:
        for idx,scene in enumerate(selected,1):
            prompt=str(scene.get("visual_prompt") or scene.get("narration") or topic)
            seconds=per_scene
            clip=work/f"clip_{idx:02d}.mp4"
            if worker_enabled:
                # Primary path: the real Wan2.1 T2V worker creates moving video for every beat.
                generated=work/f"wan_{idx:02d}.mp4"
                generate_motion_clip(prompt, str(generated), width=width, height=height, seconds=max(3,min(5,round(seconds))))
                _normalize_video(generated,clip,width,height,seconds)
            else:
                # Web-only fallback: Pexels image + motion, never black.
                img=work/f"scene_{idx:02d}.jpg"
                pexels=_pexels_image(_safe_query(prompt),orientation,img)
                if not pexels:_make_fallback_card(str(scene.get("narration") or prompt),topic,width,height,img,idx)
                _make_image_clip(img,clip,width,height,seconds,idx)
            clips.append(clip)
        silent=work/"silent.mp4"; _concat(clips,silent)
        _run([shutil.which("ffmpeg"),"-y","-i",str(silent),"-i",audio,"-t",f"{audio_seconds:.3f}","-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(out)])
    finally:
        shutil.rmtree(work,ignore_errors=True)
    return str(out)
