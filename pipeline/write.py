#!/usr/bin/env python3
"""CURATOR + EXPLAINER + SCRIPTWRITER + FACT-CHECKER (LLM stages, Gemini free tier).
-> output/script.json  (aborts the run on fact-check failure)
"""
import json
import os
import sys
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())

CURATOR_PROMPT = """You curate AI news for a faceless video channel aimed at high-school students.
Rank these stories by (1) real-world impact, (2) visual explainability, (3) novelty.
Skip pure funding-round press releases unless the amount changes the industry.
Pick the top {n}.
Stories:
{stories}
Return ONLY valid JSON: {{"picks": [{{"id": "<id>", "reason": "<one line>"}}]}}"""

EXPLAINER_PROMPT = """Explain this AI news for a smart high-schooler.
Rules: Flesch-Kincaid grade 9 or below. No unexplained jargon — every technical
term gets a one-line everyday analogy first. Lead with why a teenager should care.
120-180 words.
Story: {title}
Source summary: {summary}
Return ONLY valid JSON: {{"brief": "...", "analogy": "...", "why_it_matters": "..."}}"""

SHORT_SCRIPT_PROMPT = """Write a voiceover script for a 60-second vertical video from this brief.
Rules:
- 150-300 words total. First spoken line hooks in under 3 seconds — no intro, no greeting.
- One idea per segment, 1-2 sentences each, conversational present tense.
- End with a short follow CTA.
- Every segment needs a "broll" keyword query (2-4 words) for stock footage.
Brief: {brief}
Return ONLY valid JSON:
{{"title": "<60 chars, honest, no clickbait lies", "hook": "first line",
  "segments": [{{"text": "...", "broll": "..."}}],
  "description": "video description with sources",
  "hashtags": ["#ai", "#ainews"]}}"""

LONG_SCRIPT_PROMPT = """Write a 1500-2500 word voiceover script for a 10-minute YouTube video
covering these stories as chapters.
Rules:
- Cold open: the week's biggest story in 30 seconds, hook first.
- Chapters with spoken transitions ("meanwhile...", "here's why that matters...").
- High-school reading level, analogies for jargon, recap + follow CTA at the end.
- Every segment needs a "broll" keyword query (2-4 words) for stock footage.
Stories:
{briefs}
Return ONLY valid JSON:
{{"title": "...", "hook": "...",
  "segments": [{{"text": "...", "broll": "..."}}],
  "description": "...", "hashtags": ["#ai", "#ainews"]}}"""

FACTCHECK_PROMPT = """You are a fact-checker. Compare EVERY factual claim in this script
against the source material below. Flag anything not supported, exaggerated, or
stated with false certainty (dates, numbers, model names, company claims).
Sources:
{sources}
Script:
{script}
Return ONLY valid JSON: {{"verdict": "ok|fail", "issues": ["..."]}}"""


def llm_json(prompt: str) -> dict:
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("[write] GEMINI_API_KEY is not set")
    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        # NOTE (2026-10-06): gemini-2.5-flash is retired for new API keys;
        # gemini-3.8-flash is the current free-tier flash model.
        "gemini-3.8-flash",
        generation_config={"response_mime_type": "application/json",
                           "temperature": 0.7},
    )
    resp = model.generate_content(prompt)
    text = resp.text.strip()
    # tolerate markdown fences
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    return json.loads(text)


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    n = CFG[mode]["stories"]
    wmin, wmax = CFG[mode]["script_words"]

    stories = json.loads((ROOT / "output" / "stories.json").read_text())
    if not stories:
        sys.exit("[write] no stories to work with")

    listing = "\n".join(
        f"- id={s['id']} | {s['title']} ({s['source']}) :: {s['summary'][:250]}"
        for s in stories)
    picks = llm_json(CURATOR_PROMPT.format(n=n, stories=listing))["picks"]
    by_id = {s["id"]: s for s in stories}
    chosen = [by_id[p["id"]] for p in picks if p["id"] in by_id]
    if not chosen:
        sys.exit("[write] curator returned unknown ids — aborting")

    briefs = []
    for s in chosen:
        b = llm_json(EXPLAINER_PROMPT.format(title=s["title"], summary=s["summary"]))
        briefs.append({"story": s, **b})

    if mode == "daily":
        script = llm_json(SHORT_SCRIPT_PROMPT.format(brief=briefs[0]["brief"]))
    else:
        joined = "\n\n".join(
            f"STORY: {b['story']['title']}\n{b['brief']}" for b in briefs)
        script = llm_json(LONG_SCRIPT_PROMPT.format(briefs=joined))

    words = sum(len(seg["text"].split()) for seg in script["segments"])
    if not (wmin <= words <= wmax + 200):
        print(f"[write] WARNING: script is {words} words (target {wmin}-{wmax})")

    sources_txt = "\n\n".join(
        f"{b['story']['title']} ({b['story']['source']}, {b['story']['url']}): "
        f"{b['story']['summary']}" for b in briefs)
    script_txt = "\n".join(seg["text"] for seg in script["segments"])
    check = llm_json(FACTCHECK_PROMPT.format(sources=sources_txt, script=script_txt))
    if check.get("verdict") != "ok":
        print("[write] FACT CHECK FAILED:")
        for i in check.get("issues", []):
            print("  -", i)
        sys.exit(1)

    script["story_ids"] = [b["story"]["id"] for b in briefs]
    script["sources"] = [
        {"title": b["story"]["title"], "url": b["story"]["url"],
         "source": b["story"]["source"]} for b in briefs]
    (ROOT / "output" / "script.json").write_text(json.dumps(script, indent=2))
    print(f"[write] script ok ({words} words, {len(script['segments'])} segments)")


if __name__ == "__main__":
    main()
