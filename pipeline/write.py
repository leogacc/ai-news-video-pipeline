#!/usr/bin/env python3
"""CURATOR + EXPLAINER + SCRIPTWRITER + FACT-CHECKER (LLM stages, Gemini free tier).
-> output/script.json  (aborts the run on fact-check failure)
"""
import json
import os
import sys
import re
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())

COMBINED_PROMPT = """You are the writer for a faceless AI-news video channel aimed at high-school students.
Stories (id | title | source, then the full material you may use):
{listing}
Do these three jobs in order:
1. CURATOR — pick the {n} most important stories (real-world impact, visual explainability, novelty; skip pure funding press releases unless the amount changes the industry).
2. EXPLAINER — for each pick, a 120-180 word brief a smart high-schooler can follow: Flesch-Kincaid grade 9 or below, every technical term gets a one-line everyday analogy first, lead with why a teenager should care.
3. SCRIPTWRITER — {script_brief}
GROUNDING RULE (non-negotiable): every factual claim — numbers, dates, names, quotes, study results — must come from the MATERIAL above. If a story's material is thin (headline/summary only), keep its claims headline-level. Never invent specifics to fill space.
Return ONLY valid JSON:
{{"picks": [{{"id": "<story id>", "reason": "<one line>"}}],
  "title": "<video title, <60 chars, honest, no clickbait lies>",
  "hook": "<first spoken line, hooks in under 3 seconds>",
  "segments": [{{"text": "spoken narration", "broll": "stock footage query, 2-4 words"}}],
  "description": "video description with sources",
  "hashtags": ["#ai", "#ainews"]}}"""

SHORT_BRIEF = """a 150-300 word voiceover script for a 60-second vertical video from the brief. First spoken line hooks in under 3 seconds — no intro, no greeting. One idea per segment, 1-2 sentences each, conversational present tense. End with a short follow CTA."""
LONG_BRIEF = """a 1500-2500 word voiceover script for a 10-minute YouTube video covering the picked stories as chapters. Cold open with the biggest story in 30 seconds, hook first. Chapters with spoken transitions ("meanwhile...", "here's why that matters..."). Recap + follow CTA at the end."""

FACTCHECK_PROMPT = """You are a fact-checker. Compare EVERY factual claim in this script
against the source material below. Flag anything not supported, exaggerated, or
stated with false certainty (dates, numbers, model names, company claims).
Sources:
{sources}
Script:
{script}
Return ONLY valid JSON: {{"verdict": "ok|fail", "issues": ["..."]}}"""


_last_call = 0.0


def pace(min_gap: float = 15.0):
    """Keep calls under the free tier's ~5 req/min limit."""
    global _last_call
    dt = time.time() - _last_call
    if dt < min_gap:
        time.sleep(min_gap - dt)
    _last_call = time.time()


def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    return json.loads(text)


class _RateLimited(Exception):
    def __init__(self, msg, retry_after=None):
        super().__init__(msg)
        self.retry_after = retry_after  # seconds until quota resets, if known


def _retry_delay_seconds(msg: str) -> float | None:
    m = re.search(r"retry in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", msg)
    if not m:
        return None
    h, mi, s = m.groups()
    return int(h or 0) * 3600 + int(mi or 0) * 60 + float(s or 0)


def _gemini_call(prompt: str) -> dict:
    import requests
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise _RateLimited("no GEMINI_API_KEY")
    url = ("https://generativelanguage.googleapis.com/v1beta/"
           "models/gemini-3.8-flash:generateContent")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json",
                             "temperature": 0.7},
    }
    r = requests.post(url, params={"key": key}, json=body, timeout=120)
    if r.status_code in (429, 500, 503):
        raise _RateLimited(f"Gemini HTTP {r.status_code}",
                           retry_after=_retry_delay_seconds(r.text))
    r.raise_for_status()
    return _parse_json(r.json()["candidates"][0]["content"]["parts"][0]["text"])


def _pollinations_call(prompt: str) -> dict:
    """Keyless fallback when Gemini's free quota is exhausted."""
    import requests
    r = requests.post(
        "https://text.pollinations.ai/",
        json={"messages": [{"role": "user", "content": prompt}],
              "model": "openai", "private": True},
        timeout=180)
    if r.status_code in (429, 500, 503):
        raise _RateLimited(f"pollinations HTTP {r.status_code}")
    r.raise_for_status()
    return _parse_json(r.text)


def llm_json(prompt: str) -> dict:
    """Gemini first (best quality). On quota exhaustion: try the keyless
    fallback, then sleep until Gemini's quota resets and try again.
    Patient up to ~5.5h (inside the 6h job cap) — a run that hits an empty
    quota still completes the same day instead of failing.
    One request per attempt, 65s+ spacing — never a retry storm."""
    last: Exception = RuntimeError("no attempts made")
    deadline = time.time() + 5.5 * 3600
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        # 1) Gemini, paced to the per-minute quota
        pace(65)
        try:
            return _gemini_call(prompt)
        except _RateLimited as e:
            print(f"[write] {e} (attempt {attempt}, gemini)")
            last = e
            if (e.retry_after and e.retry_after > 120
                    and e.retry_after < deadline - time.time() - 600):
                wait = e.retry_after + 60
                print(f"[write] quota resets in ~{wait / 3600:.1f}h — "
                      f"sleeping until then")
                time.sleep(wait)
                continue
        except Exception as e:
            if "Timeout" in type(e).__name__:
                print(f"[write] transient ({e}), retrying")
                last = e
                continue
            raise
        # 2) keyless fallback while Gemini is exhausted
        pace(30)
        try:
            return _pollinations_call(prompt)
        except _RateLimited as e:
            print(f"[write] {e} (attempt {attempt}, fallback)")
            last = e
        except Exception as e:
            if "Timeout" in type(e).__name__:
                print(f"[write] transient ({e}), retrying")
                last = e
            else:
                raise
        time.sleep(60)
    raise last


def story_material(s: dict) -> str:
    """Full article text when ingest fetched it, else the RSS summary.
    The fact-checker compares every claim against exactly this material."""
    body = (s.get("body") or "").strip()
    if body:
        return body[:2500]
    return (s.get("summary") or "").strip()[:600]


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    n = CFG[mode]["stories"]
    wmin, wmax = CFG[mode]["script_words"]

    stories = json.loads((ROOT / "output" / "stories.json").read_text())
    if not stories:
        sys.exit("[write] no stories to work with")

    listing = "\n\n".join(
        f"--- id={s['id']} | {s['title']} ({s['source']})\n"
        f"MATERIAL:\n{story_material(s)}"
        for s in stories)
    brief = SHORT_BRIEF if mode == "daily" else LONG_BRIEF
    # Curator + Explainer + Scriptwriter in ONE call: the free tier only
    # allows ~20 requests/day, so every call counts.
    script = llm_json(COMBINED_PROMPT.format(n=n, listing=listing,
                                            script_brief=brief))
    by_id = {s["id"]: s for s in stories}

    def validate(script_obj: dict) -> list:
        picks = [p for p in script_obj.get("picks", []) if p["id"] in by_id]
        return [by_id[p["id"]] for p in picks]

    chosen = validate(script)
    if not chosen:
        sys.exit("[write] no valid story picks — aborting")

    words = sum(len(seg["text"].split()) for seg in script["segments"])
    if not (wmin <= words <= wmax + 200):
        print(f"[write] WARNING: script is {words} words (target {wmin}-{wmax})")

    def factcheck(script_obj: dict, chosen_stories: list) -> dict:
        sources_txt = "\n\n".join(
            f"--- {s['title']} ({s['source']}, {s['url']})\n{story_material(s)}"
            for s in chosen_stories)
        script_txt = "\n".join(seg["text"] for seg in script_obj["segments"])
        return llm_json(FACTCHECK_PROMPT.format(sources=sources_txt,
                                               script=script_txt))

    check = factcheck(script, chosen)
    if check.get("verdict") != "ok":
        # One repair pass: hand the issues back to the writer instead of
        # aborting the whole run on the first draft's hallucinations.
        issues = check.get("issues", [])
        print("[write] fact-check flagged issues — one repair pass:")
        for i in issues:
            print("  -", i)
        repair_prompt = (COMBINED_PROMPT.format(n=n, listing=listing,
                                               script_brief=brief)
                         + "\n\nREVISION REQUIRED. The fact-checker flagged "
                           "these issues in your draft:\n- "
                         + "\n- ".join(issues)
                         + "\nFix every issue: remove or soften unsupported "
                           "claims. Keep the same JSON shape and story picks.")
        script = llm_json(repair_prompt)
        chosen = validate(script)
        if not chosen:
            sys.exit("[write] no valid story picks after repair — aborting")
        check = factcheck(script, chosen)
        if check.get("verdict") != "ok":
            print("[write] FACT CHECK FAILED after repair:")
            for i in check.get("issues", []):
                print("  -", i)
            sys.exit(1)
        print("[write] repair pass accepted")

    script["story_ids"] = [s["id"] for s in chosen]
    script["sources"] = [
        {"title": s["title"], "url": s["url"], "source": s["source"]}
        for s in chosen]
    (ROOT / "output" / "script.json").write_text(json.dumps(script, indent=2))
    print(f"[write] script ok ({words} words, {len(script['segments'])} segments)")


if __name__ == "__main__":
    main()
