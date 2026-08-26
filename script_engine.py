"""Local-first script and scene planner.
No paid API is required. If an optional local LLM endpoint is configured, it is
used; otherwise a useful deterministic documentary script is generated.
"""
from __future__ import annotations
import os, requests
from textwrap import fill

def generate_script(topic: str, duration_seconds: int, style: str = "cinematic documentary") -> str:
    topic=topic.strip()
    minutes=max(1, round(duration_seconds/60))
    endpoint=os.getenv("LOCAL_LLM_URL")
    if endpoint:
        try:
            prompt=(f"Write a {minutes}-minute {style} YouTube narration about: {topic}. "
                    "Start with a strong hook, use clear sections, examples and a conclusion. "
                    "Return narration only, no stage directions.")
            r=requests.post(endpoint,json={"prompt":prompt},timeout=120); r.raise_for_status()
            data=r.json(); text=data.get("text") or data.get("response") or data.get("content")
            if text: return text.strip()
        except Exception:
            pass
    hook=f"What if the thing you think is helping you is actually keeping you stuck? Today, we're looking at {topic}."
    sections=[
        f"{hook}",
        f"Let's start with the uncomfortable part: {topic} is rarely caused by one bad decision. It is usually a pattern of small decisions that become normal.",
        f"First, look at the incentives. When people experience a change related to {topic}, they often change their behavior before they change their underlying habits.",
        f"Second, look at the psychology. We tend to adapt quickly to improvements and then treat them as the new normal. That can make progress feel invisible even when the numbers change.",
        f"Third, look at the practical choices. A useful approach is to separate what creates short-term comfort from what creates long-term freedom. That distinction changes how you respond to {topic}.",
        f"So what should you do? Start small. Measure the behavior, remove one unnecessary expense or distraction, and redirect the difference toward a goal that compounds.",
        f"The bigger lesson from {topic} is simple: changing the amount of money, time, or attention you have does not automatically change the system you use it with.",
        "If this helped, use the idea on one decision this week. The goal is not perfection. The goal is to build a system that keeps working after motivation disappears."
    ]
    target=max(500, int(duration_seconds*2.2))
    text="\n\n".join(sections)
    while len(text.split())<target:
        text += "\n\n" + sections[len(text.split()) % (len(sections)-1)+1]
    return " ".join(text.split()[:target])

def scene_plan(script: str, max_words: int = 90) -> list[dict]:
    words=script.split(); scenes=[]
    for i in range(0,len(words),max_words):
        chunk=" ".join(words[i:i+max_words])
        scenes.append({"scene":len(scenes)+1,"narration":chunk,"visual_prompt":f"Cinematic realistic documentary visuals illustrating: {chunk[:220]}"})
    return scenes
