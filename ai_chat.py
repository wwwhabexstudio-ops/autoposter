"""AI Coach with a zero-cost fallback and optional local Ollama backend."""
from __future__ import annotations
import os
import requests


def chat(message: str, context: str = "") -> str:
    """Use local Ollama when configured; otherwise provide a useful rule-based coach."""
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    try:
        r = requests.post(f"{host}/api/generate", json={
            "model": model,
            "prompt": f"You are AutoPoster AI Coach. Give concise, practical content strategy advice.\nContext: {context}\nUser: {message}",
            "stream": False,
        }, timeout=8)
        if r.ok:
            data = r.json()
            if data.get("response"):
                return data["response"].strip()
    except requests.RequestException:
        pass
    return fallback(message)


def fallback(message: str) -> str:
    q = message.lower()
    if "what should i post" in q or "idea" in q:
        return "Start with a problem your audience already cares about. Test 3 different hooks around one topic, then let your analytics decide which pattern deserves another batch."
    if "best time" in q or "when" in q:
        return "I won't invent a best time. AutoPoster should recommend a window only after enough historical posts exist for that weekday/hour."
    if "hook" in q:
        return "Try a specific curiosity gap: state the surprising outcome first, then promise the explanation. Avoid misleading clickbait."
    return "I can help with hooks, titles, captions, scripts, experiments and posting strategy. Connect a local Ollama model for full conversational AI without a paid API."
