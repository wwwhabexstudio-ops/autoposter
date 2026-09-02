"""Script + scene generation with strict requested-duration control."""
from __future__ import annotations
import json, os, re, requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
WORDS_PER_SECOND = 2.25


def _gemini(prompt: str) -> str | None:
    key = os.getenv("GEMINI_API_KEY")
    if not key: return None
    try:
        r = requests.post(f"{GEMINI_URL}?key={key}", json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=180)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None


def fit_script_to_duration(text: str, duration_seconds: int) -> str:
    target = max(30, round(duration_seconds * WORDS_PER_SECOND))
    words = re.findall(r"\S+", text.strip())
    if len(words) <= target: return " ".join(words)
    clipped = " ".join(words[:target])
    last = max(clipped.rfind("."), clipped.rfind("!"), clipped.rfind("?"))
    if last >= int(len(clipped) * 0.72): clipped = clipped[:last + 1]
    return clipped.strip()


def generate_script(topic: str, duration_seconds: int, style: str = "cinematic documentary") -> str:
    topic = topic.strip()
    target_words = max(30, round(duration_seconds * WORDS_PER_SECOND))
    prompt = (
        f"Write a compelling {duration_seconds}-second {style} narration about '{topic}'. "
        f"Write approximately {target_words} spoken words and never exceed {target_words} words. "
        "Use a strong hook, one clear story, concrete examples, a useful payoff, and a concise CTA. "
        "No headings, stage directions, repetition, or filler."
    )
    ai = _gemini(prompt)
    if ai: return fit_script_to_duration(ai, duration_seconds)
    endpoint = os.getenv("LOCAL_LLM_URL")
    if endpoint:
        try:
            r = requests.post(endpoint, json={"prompt":prompt}, timeout=120); r.raise_for_status()
            data = r.json(); text = data.get("text") or data.get("response") or data.get("content")
            if text: return fit_script_to_duration(text.strip(), duration_seconds)
        except Exception: pass
    sections = [
        f"What if the reason people struggle with {topic} is not what you think?",
        f"The uncomfortable truth is that {topic} is rarely one dramatic decision. It is usually a pattern of small choices repeated until they feel normal.",
        "Those choices compound. A decision that looks harmless today can quietly shape the options you have months or years later.",
        "The useful question is not whether you are perfect. It is whether your everyday system is moving you toward the result you actually want.",
        "Start with one measurable change. Remove one harmful habit, protect one useful habit, and repeat it long enough for the result to become visible.",
        f"That is the bigger lesson behind {topic}: lasting progress comes from changing the system, not waiting for motivation to rescue you.",
        "If this helped, follow for more practical ideas, and comment what topic you want me to break down next."
    ]
    text = " ".join(sections)
    while len(text.split()) < target_words: text += " " + sections[len(text.split()) % len(sections)]
    return fit_script_to_duration(text, duration_seconds)


def scene_plan(script: str, max_words: int = 10_000) -> list[dict]:
    words = script.split(); scenes=[]
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        scenes.append({"scene":len(scenes)+1, "narration":chunk,
          "visual_prompt":f"cinematic realistic moving documentary shot illustrating: {chunk[:260]}; no text, no subtitles, no typography, no title card, no infographic"})
    return scenes


def generate_scene_plan_ai(script: str, style: str) -> list[dict]:
    prompt=("Turn this narration into semantic cinematic scene ideas for a REAL AI text-to-video model. Return JSON only. "
            "Each object must contain scene, narration, visual_prompt, camera_motion, mood. "
            "Do not put more than 2 sentences in a scene. Each visual must be concrete, different, physically observable, "
            "and directly illustrate its narration. Describe people, places, objects, actions, lighting, camera movement and composition. "
            "CRITICAL: generate actual moving imagery prompts, NOT text cards. Never request or include readable text, captions, subtitles, "
            "letters, numbers, logos, UI, charts, diagrams, title cards, quote cards, presentation slides, or typography in the visuals. "
            f"Style: {style}. Narration:\n{script}")
    raw=_gemini(prompt)
    if raw:
        try:
            data=json.loads(raw.replace("```json","").replace("```","").strip())
            if isinstance(data,list): return data
        except Exception: pass
    return scene_plan(script)
