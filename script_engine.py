"""Script + scene generation with a free-first AI provider and local fallback.

If GEMINI_API_KEY is configured, Gemini generates the script/scene plan. The
free Gemini API tier is used; quotas still apply. No key is stored in source.
If no key is configured, the deterministic generator keeps the app usable.
"""
from __future__ import annotations
import json, os, requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _gemini(prompt: str) -> str | None:
    key=os.getenv("GEMINI_API_KEY")
    if not key: return None
    try:
        r=requests.post(f"{GEMINI_URL}?key={key}", json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=180)
        r.raise_for_status()
        data=r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None


def generate_script(topic: str, duration_seconds: int, style: str = "cinematic documentary") -> str:
    topic=topic.strip(); minutes=max(1, round(duration_seconds/60))
    prompt=(f"Write a compelling {minutes}-minute {style} video narration about '{topic}'. "
            "Target a natural spoken pace. Start with a strong curiosity hook. Build clear chapters, "
            "specific examples and useful takeaways. Avoid unsupported statistics. End with a concise CTA. "
            "Return narration only, no stage directions, no markdown headings.")
    ai=_gemini(prompt)
    if ai: return ai
    endpoint=os.getenv("LOCAL_LLM_URL")
    if endpoint:
        try:
            r=requests.post(endpoint,json={"prompt":prompt},timeout=120); r.raise_for_status()
            data=r.json(); text=data.get("text") or data.get("response") or data.get("content")
            if text: return text.strip()
        except Exception: pass
    hook=f"What if the thing you think is helping you is actually keeping you stuck? Today, we're looking at {topic}."
    sections=[hook,
      f"Let's start with the uncomfortable part: {topic} is rarely caused by one bad decision. It is usually a pattern of small decisions that become normal.",
      f"First, look at the incentives. When people experience a change related to {topic}, they often change their behavior before they change their underlying habits.",
      f"Second, look at the psychology. We adapt quickly to improvements and can treat them as the new normal, making progress feel invisible even when the numbers change.",
      f"Third, look at the practical choices. Separate short-term comfort from long-term freedom, then direct a measurable amount toward the outcome that compounds.",
      f"So what should you do? Start small. Measure the behavior, remove one unnecessary expense or distraction, and redirect the difference toward a goal that compounds.",
      f"The bigger lesson from {topic} is simple: changing the amount of money, time, or attention you have does not automatically change the system you use it with.",
      "If this helped, use the idea on one decision this week. The goal is not perfection. The goal is to build a system that keeps working after motivation disappears."]
    target=max(500,int(duration_seconds*2.2)); text="\n\n".join(sections)
    while len(text.split())<target: text += "\n\n" + sections[(len(text.split())//100)%len(sections)]
    return " ".join(text.split()[:target])


def scene_plan(script: str, max_words: int = 70) -> list[dict]:
    words=script.split(); scenes=[]
    for i in range(0,len(words),max_words):
        chunk=" ".join(words[i:i+max_words])
        scenes.append({"scene":len(scenes)+1,"narration":chunk,
          "visual_prompt":f"{os.getenv('VIDEO_STYLE','cinematic realistic')} moving documentary shot illustrating: {chunk[:260]}",
          "duration_seconds":max(3,min(10,round(len(chunk.split())/2.4)))})
    return scenes


def generate_scene_plan_ai(script: str, style: str) -> list[dict]:
    prompt=("Turn this narration into a JSON array of cinematic video scenes. "
            "Each object must contain scene, narration, visual_prompt, camera_motion, mood, duration_seconds. "
            f"Style: {style}. Keep visual prompts concrete and safe. Narration:\n{script}")
    raw=_gemini(prompt)
    if raw:
        try:
            raw=raw.replace("```json","").replace("```","").strip()
            data=json.loads(raw)
            if isinstance(data,list): return data
        except Exception: pass
    return scene_plan(script)
