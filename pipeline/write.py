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
Stories (id | title | source | summary):
{listing}
Do these three jobs in order:
1. CURATOR — pick the {n} most important stories (real-world impact, visual explainability, novelty; skip pure funding press releases unless the amount changes the industry). STRONGLY prefer stories with full article text included below — headline-only stories are a last resort.
2. EXPLAINER — for each pick, a 120-180 word brief a smart high-schooler can follow: Flesch-Kincaid grade 8 or below, every technical term gets a one-line everyday analogy first, lead with why a teenager should care.
3. SCRIPTWRITER — {script_brief} Group segments by story in picks order; every segment carries the story_id of the story it covers. Each segment's "broll" is a 3-5 word stock-footage query naming the CONCRETE subject on screen — a person, company, place, or object (e.g. "Elon Musk portrait", "SpaceX rocket launch", "chalkboard math equations", "Hong Kong skyline night"). Never generic filler like "technology", "future", "student studying", "abstract".
HONESTY RULE (non-negotiable): only state facts present in the provided material. Never invent numbers, quotes, dates, names, or specifics that aren't in the sources. If a story's material is thin (headline only), write a SHORTER script from just what's there rather than padding with invented detail — a 90-word honest script beats a 250-word fabricated one.
Return ONLY valid JSON:
{{"picks": [{{"id": "<story id>", "reason": "<one line>"}}],
  "title": "<video title, <60 chars, honest, no clickbait lies>",
  "hook": "<first spoken line, hooks in under 3 seconds>",
  "segments": [{{"text": "spoken narration", "broll": "concrete stock-footage query naming the subject, 3-5 words", "story_id": "<id of the story this segment covers>"}}],
  "description": "video description with sources",
  "hashtags": ["#ai", "#ainews"]}}"""

SHORT_BRIEF = """a 200-350 word voiceover script for a 90-second vertical video covering the 5 picked stories rapid-fire. First spoken line hooks in under 3 seconds — no intro, no greeting. Each story gets 1-2 segments: one striking fact plus one line on why it matters, conversational present tense. End with a short follow CTA."""
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


def llm_json(prompt: str, deadline: float | None = None) -> dict:
    """Gemini first (best quality). On quota exhaustion: try the keyless
    fallback, then sleep until Gemini's quota resets and try again.
    Patient up to ~5.5h (inside the 6h job cap) — a run that hits an empty
    quota still completes the same day instead of failing.
    One request per attempt, 65s+ spacing — never a retry storm.
    Pass a shared deadline when several calls must fit one budget."""
    last: Exception = RuntimeError("no attempts made")
    deadline = deadline or time.time() + 5.5 * 3600
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


SIMPLIFY_PROMPT = """Rewrite these video narration segments in simpler language a 13-year-old can easily follow.

Rules:
- Keep the SAME number of segments in the SAME order.
- Keep every fact exactly the same — change wording only. Add no new facts, drop no facts.
- Keep each segment's "broll" query and "story_id" EXACTLY as-is (character for character).
- Use short sentences (under 18 words each) and everyday words. Flesch-Kincaid grade 8 or below.
- Keep the total word count within 10% of the original.

Output ONLY this JSON, nothing else:
{{"segments": [{{"text": "...", "broll": "...", "story_id": "..."}}, ...]}}

Segments (story_id shown for preservation, do not change):
{segments}
"""


REVISE_PROMPT = """You wrote a video script that a fact-checker reviewed. Fix ONLY the issues listed below — keep every other segment, word, "broll" query, and "story_id" exactly the same unless an issue forces a change. Do not add new facts.

Issues:
{issues}

Current script JSON:
{script_json}

Output ONLY the corrected JSON with the same shape:
{{"picks": [...], "title": "...", "hook": "...", "segments": [{{"text": "...", "broll": "...", "story_id": "..."}}], "description": "...", "hashtags": [...]}}"""


def fact_check_ok(sources_txt: str, script: dict, deadline) -> bool:
    """Run the fact-checker; on failure, print issues and return False."""
    script_txt = "\n".join(seg["text"] for seg in script["segments"])
    check = llm_json(FACTCHECK_PROMPT.format(sources=sources_txt,
                                            script=script_txt),
                     deadline=deadline)
    if check.get("verdict") == "ok":
        return True
    print("[write] FACT CHECK FAILED:")
    for i in check.get("issues", []):
        print("  -", i)
    script["_fc_issues"] = check.get("issues", [])
    return False


def simplify_main():
    """SIMPLIFY=1: rewrite the existing script.json in simpler language and
    re-fact-check it against the same sources. Used by the run.py retry loop
    when QA blocks only on reading level."""
    script = json.loads((ROOT / "output" / "script.json").read_text())
    stories = {s["id"]: s for s in
               json.loads((ROOT / "output" / "stories.json").read_text())}
    chosen = [stories[i] for i in script.get("story_ids", []) if i in stories]
    segs_txt = "\n".join(
        f'{i + 1}. story_id="{s.get("story_id", "")}" '
        f'text="{s["text"]}" broll="{s["broll"]}"'
        for i, s in enumerate(script["segments"]))
    new = llm_json(SIMPLIFY_PROMPT.format(segments=segs_txt))
    segs = new.get("segments") or []
    if len(segs) != len(script["segments"]) or \
            not all(s.get("text") and s.get("broll") for s in segs):
        sys.exit("[write] simplify produced invalid segments — aborting")
    script["segments"] = [{"text": s["text"], "broll": s["broll"],
                           "story_id": s.get("story_id")
                           or script["segments"][i].get("story_id")}
                          for i, s in enumerate(segs)]
    sources_txt = "\n\n".join(
        f"{s['title']} ({s['source']}, {s['url']}):\n"
        f"Summary: {s['summary'][:400]}\n"
        f"Article: {(s.get('article') or '[not available]')[:2500]}"
        for s in chosen)
    if not fact_check_ok(sources_txt, script, time.time() + 5.5 * 3600):
        sys.exit(1)
    (ROOT / "output" / "script.json").write_text(json.dumps(script, indent=2))
    words = sum(len(s["text"].split()) for s in script["segments"])
    print(f"[write] simplified script ok ({words} words, "
          f"{len(script['segments'])} segments)")


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    if os.environ.get("SIMPLIFY") == "1":
        simplify_main()
        return
    n = CFG[mode]["stories"]
    wmin, wmax = CFG[mode]["script_words"]

    stories = json.loads((ROOT / "output" / "stories.json").read_text())
    if not stories:
        sys.exit("[write] no stories to work with")

    listing = "\n\n".join(
        f"--- STORY id={s['id']} "
        f"[{'FULL ARTICLE' if s.get('article') else 'HEADLINE ONLY'}] ---\n"
        f"Title: {s['title']}\n"
        f"Source: {s['source']}\nSummary: {s['summary'][:400]}\n"
        f"Article text: {(s.get('article') or '[not available]')[:2500]}"
        for s in stories)
    brief = SHORT_BRIEF if mode == "daily" else LONG_BRIEF
    # Curator + Explainer + Scriptwriter in ONE call: the free tier only
    # allows ~20 requests/day, so every call counts.
    # The keyless fallback can return malformed picks (wrong ids) when
    # Gemini is rate-limited — that's transient, not fatal, so retry the
    # combined call a few times within the shared deadline before giving up
    # (a single bad-picks abort is what killed run #8).
    deadline = time.time() + 5.5 * 3600
    by_id = {s["id"]: s for s in stories}
    script, picks = None, []
    for combo_try in range(1, 4):
        script = llm_json(COMBINED_PROMPT.format(n=n, listing=listing,
                                                script_brief=brief),
                         deadline=deadline)
        picks = [p for p in script.get("picks", [])
                 if isinstance(p, dict) and p.get("id") in by_id]
        if picks:
            break
        print(f"[write] no valid story picks (try {combo_try}) — retrying")
    if not picks:
        sys.exit("[write] no valid story picks — aborting")
    chosen = [by_id[p["id"]] for p in picks]

    words = sum(len(seg["text"].split()) for seg in script["segments"])
    if words > wmax + 200:
        print(f"[write] WARNING: script is {words} words (target {wmin}-{wmax})")
    # (Shorter than wmin is fine: the honesty rule beats the word target.)

    sources_txt = "\n\n".join(
        f"{s['title']} ({s['source']}, {s['url']}):\n"
        f"Summary: {s['summary'][:400]}\n"
        f"Article: {(s.get('article') or '[not available]')[:2500]}"
        for s in chosen)
    # Fact-check with revision loop: the checker returns specific, fixable
    # issues (a reversed attribution killed run #11), so give the writer up
    # to 2 revision tries before aborting the run.
    for fc_try in range(1, 4):
        if fact_check_ok(sources_txt, script, deadline):
            break
        if fc_try == 3:
            sys.exit(1)
        print(f"[write] revising script per fact-check (try {fc_try})")
        rev = llm_json(REVISE_PROMPT.format(
            issues="\n".join("- " + i for i in script.pop("_fc_issues")),
            script_json=json.dumps(
                {k: script[k] for k in
                 ("picks", "title", "hook", "segments",
                  "description", "hashtags") if k in script},
                indent=2)), deadline=deadline)
        if not rev.get("segments"):
            print("[write] revision produced no segments — aborting")
            sys.exit(1)
        for k in ("title", "hook", "description", "hashtags"):
            if k in rev:
                script[k] = rev[k]
        # preserve story_id per segment (fall back to original by index)
        old_segs = script["segments"]
        new_segs = rev["segments"]
        if len(new_segs) != len(old_segs):
            print("[write] revision changed segment count — aborting")
            sys.exit(1)
        script["segments"] = [
            {"text": s.get("text", ""), "broll": s.get("broll", ""),
             "story_id": s.get("story_id") or old_segs[i].get("story_id")}
            for i, s in enumerate(new_segs)]

    script["story_ids"] = [s["id"] for s in chosen]
    script["sources"] = [
        {"title": s["title"], "url": s["url"], "source": s["source"],
         "x_media_url": s.get("x_media_url")}
        for s in chosen]
    (ROOT / "output" / "script.json").write_text(json.dumps(script, indent=2))
    print(f"[write] script ok ({words} words, {len(script['segments'])} segments)")


if __name__ == "__main__":
    main()
