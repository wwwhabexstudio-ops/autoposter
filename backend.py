from pathlib import Path
from datetime import datetime, timezone
from database import add_post
from content_pipeline import create_project
from video_lab import SUPPORTED_ASPECT_RATIOS
from tts_engine import generate_voiceover
from script_engine import generate_script, generate_scene_plan_ai
from platform_intelligence import generate_metadata
from brand_overlay import add_logo
from image_video_pipeline import render_from_scenes

BASE_DIR=Path(__file__).parent
VIDEO_DIR=BASE_DIR/'data'/'videos'; RENDER_DIR=BASE_DIR/'data'/'renders'; ASSET_DIR=BASE_DIR/'data'/'assets'; CLIP_DIR=BASE_DIR/'data'/'clips'
for d in (VIDEO_DIR,RENDER_DIR,ASSET_DIR,CLIP_DIR): d.mkdir(parents=True,exist_ok=True)
PLATFORMS=['youtube','instagram','facebook','tiktok','linkedin']

def build_video(topic, script, duration, video_type, ratio, style, voice, visual_mode, logo_file=None):
    project=create_project(topic,script,video_type.lower(),int(duration),topic,platforms=['youtube'])
    project.video_plan.aspect_ratio=ratio; project.video_plan.width,project.video_plan.height=SUPPORTED_ASPECT_RATIOS[ratio]; project.save()
    scenes=generate_scene_plan_ai(script,style)
    safe=''.join(c if c.isalnum() else '_' for c in topic)[:55] or 'video'
    audio=VIDEO_DIR/f'{safe}_voice.wav'; final=RENDER_DIR/f'{safe}_{ratio.replace(":","x")}.mp4'
    generate_voiceover(script,str(audio),voice=voice)
    w,h=SUPPORTED_ASPECT_RATIOS[ratio]
    if visual_mode=='AI Images + 3–5 sec motion': render_from_scenes(scenes,str(audio),str(final),str(ASSET_DIR),str(CLIP_DIR),w,h)
    else:
        from video_factory import make_video
        make_video(str(audio),str(final),w,h)
    if logo_file:
        lp=ASSET_DIR/('brand_logo'+Path(logo_file.name).suffix); lp.write_bytes(logo_file.getbuffer())
        branded=RENDER_DIR/f'{safe}_{ratio.replace(":","x")}_branded.mp4'; add_logo(str(final),str(lp),str(branded)); final=branded
    return final, scenes

def queue_video(final,title,description,hashtags,platforms):
    now=datetime.now(timezone.utc).isoformat(); name=Path(final).name; target=VIDEO_DIR/name
    if Path(final).resolve()!=target.resolve(): target.write_bytes(Path(final).read_bytes())
    return add_post({'filename':name,'title':title,'description':description,'hashtags':hashtags,'platforms':platforms,'scheduled_at':None,'status':'queued','created_at':now,'updated_at':now})
