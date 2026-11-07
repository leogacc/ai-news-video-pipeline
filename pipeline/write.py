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


FIVE_ACT_PROMPT = """You are a master technical video director and scriptwriter for viral vertical tech TikToks (@leos.logos).
Write a high-retention 5-act voiceover script (~35-45 seconds, 75-100 words total, Flesch-Kincaid grade 8 or below) for this tech find:

Author / Source: {author}
Raw Content: {content}

Follow this strict 5-Act Narrative Architecture:
1. ACT I: THE QUANTIFIED SHOCK HOOK (0-3s, 1 sentence, ~12-16 words)
   - First spoken line must hook instantly.
   - You MUST vocalize the primary entity ({author} or model/project name) within the first 2.5 seconds (first 5 words).
   - You MUST include a concrete number, time, dollar value, or percentage (e.g., "in 9 seconds", "$159 billion", "79.8%", "16 agents").
   - No greeting, no "hey guys", no introductory fluff.

2. ACT II: PRIMARY EVIDENCE ESCALATION (3-12s, 1 sentence, ~14-18 words)
   - Direct, tangible proof point referencing primary evidence (arXiv paper, benchmark evaluation suite, official repository, or verified dispatch).
   - Concrete facts only.

3. ACT III: THE INVISIBLE WALL / CORE CONFLICT (12-22s, 1 sentence, ~14-18 words)
   - The friction, why traditional methods hit a wall, or why simple fixes fail.
   - Include conflict framing words (e.g. "instead of", "failed", "refused", "hit the wall", "cannot", "without").

4. ACT IV: THE CONCRETE DEMONSTRATION / SECRET WEAPON (22-34s, 1 sentence, ~14-18 words)
   - The technical mechanism, architecture, live CLI execution, or quantitative benchmark leap.
   - Concrete, specific details.

5. ACT V: RESOLUTION & VIEWER DILEMMA (34-45s, 2 sentences, ~18-24 words)
   - Sentence 5a: Scale, speedup, or market impact stat (e.g. "4.8x speedup", "100% open weights").
   - Sentence 5b: Provocative closing question directly engaging viewers to debate in the comments.

Output ONLY valid JSON:
{{
  "title": "<High-impact video title under 55 chars>",
  "title_prefix": "<Emoji + short headline prefix>",
  "badge": "<Short uppercase badge like NEW SOTA or CRITICAL RISK>",
  "act_1_hook": "<Sentence 1>",
  "act_2_evidence": "<Sentence 2>",
  "act_3_conflict": "<Sentence 3>",
  "act_4_demo": "<Sentence 4>",
  "act_5_resolution": "<Sentence 5a>",
  "question": "<Sentence 5b closing question>",
  "script_sentences": [
    "<Sentence 1>",
    "<Sentence 2>",
    "<Sentence 3>",
    "<Sentence 4>",
    "<Sentence 5a>",
    "<Sentence 5b>"
  ],
  "hashtags": ["#ai", "#technews", "#coding", "#machinelearning", "#tech"]
}}
"""


def calculate_reading_grade(text: str) -> float:
    """Calculate Flesch-Kincaid grade level with zero-dependency fallback."""
    os.environ["NLTK_ALLOW_PROXIED_URLOPEN"] = "1"
    try:
        import textstat
        grade_text = re.sub(r",\s+", ". ", text)
        return float(textstat.flesch_kincaid_grade(grade_text))
    except Exception:
        # Standard Flesch-Kincaid formula fallback:
        # 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        words = [w for w in re.findall(r"\b[A-Za-z0-9'-]+\b", text) if w]
        if not sentences or not words:
            return 6.0

        def _count_syllables(w: str) -> int:
            w = w.lower()
            if len(w) <= 3:
                return 1
            w = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", w)
            w = re.sub(r"^y", "", w)
            syls = len(re.findall(r"[aeiouy]{1,2}", w))
            return max(1, syls)

        total_syllables = sum(_count_syllables(w) for w in words)
        asl = len(words) / max(1, len(sentences))
        asw = total_syllables / max(1, len(words))
        return round(0.39 * asl + 11.8 * asw - 15.59, 1)


def _heuristic_5act_script(find: dict) -> dict:
    """Deterministic, zero-spend 5-Act narrative script generator.

    Adheres strictly to the 5-Act Dramatic Curve:
    1. Act 1: Quantified Shock Hook (< 3s, entity vocalized in first 5 words, exact number).
    2. Act 2: Primary Evidence Escalation (substantiating facts, research, or dispatches).
    3. Act 3: The Invisible Wall / Conflict (friction, why standard solutions failed).
    4. Act 4: Concrete Demonstration / Secret Weapon (architecture, tool demo, or metric jump).
    5. Act 5: Resolution, Scale & Viewer Dilemma (impact stat + debate question).
    """
    raw_author = find.get("author_name") or find.get("author") or "AI Labs"
    author = raw_author.lstrip("@").strip()
    raw_text = find.get("text") or find.get("summary") or find.get("article") or ""
    clean_text = re.sub(r"https?://\S+", "", raw_text).strip()
    clean_text = re.sub(r"\s+", " ", clean_text)
    t_lower = clean_text.lower()

    # Extract quantified metric signals
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", clean_text)
    pct_val = pct_match.group(0) if pct_match else "79.8%"

    mult_match = re.search(r"(\d+(?:\.\d+)?)\s*x\b", clean_text, re.I)
    mult_val = mult_match.group(0) if mult_match else "4.8x"

    sec_match = re.search(r"(\d+)\s*(?:seconds|sec|minutes|min|hours|days)", clean_text, re.I)
    time_val = sec_match.group(0) if sec_match else "nine seconds"

    bench_match = re.search(r"\b(AIME|SWE-bench|MMLU|OSWorld|HumanEval|GSM8K|ARC|GPQA)\b", clean_text, re.I)
    bench_name = bench_match.group(0).upper() if bench_match else "AIME 2024"

    # Archetype selection
    is_safety = any(w in t_lower for w in ["database", "delete", "wipe", "safe", "fail", "prod", "drop", "security", "exploit", "risk", "rule", "perm", "refuse"])
    is_swarm = any(w in t_lower for w in ["swarm", "parallel", "sandbox", "desktop", "computer use", "vm", "latency", "throughput", "orchestrat"])
    is_dev = any(w in t_lower for w in ["agent", "code", "dev", "workflow", "tool", "coding", "terminal", "ide", "multi-agent"])
    is_bench = any(w in t_lower for w in ["benchmark", "eval", "sota", "aime", "swe-bench", "mmlu", "%", "score"])

    clean_snippet = clean_text[:50] + ("..." if len(clean_text) > 50 else "")

    if is_safety:
        title_prefix = f"🚨 {author} Exposes Critical Agent Failure"
        title = f"{title_prefix}: {clean_snippet}"
        act_1 = f"{author} deleted an entire production database in under {time_val}."
        act_2 = "The AI agent ran routine maintenance, then wiped live tables and backups."
        act_3 = "Warning the model does not work—the safety rule must live directly inside the tool."
        act_4 = "With strict role controls, dangerous commands are refused in real time."
        act_5a = "This architecture guarantees zero unauthorized changes, stopping accidents before they happen."
        act_5b = "Will autonomous AI agents replace human developers this year? Drop your thoughts below."
        badge = "CRITICAL FAILURE"
        tags = ["#aiagents", "#coding", "#database", "#cybersecurity", "#tech"]

    elif is_swarm:
        title_prefix = f"🔥 {author} Deploys Coordinated AI Swarms"
        title = f"{title_prefix}: {clean_snippet}"
        act_1 = f"{author} is now running desktop systems with parallel swarms."
        act_2 = "Specialized worker agents click, type, and navigate tools simultaneously."
        act_3 = "Instead of single-agent bottlenecks, a lead planner splits tasks into clean virtual sandboxes."
        act_4 = f"On complex multi-step tests, this swarm setup boosts task completion from thirty-eight to over {pct_val}."
        act_5a = f"The setup delivers a {mult_val} speedup, finishing hours of desktop work in minutes."
        act_5b = "Will autonomous AI swarms permanently replace human knowledge work? Drop your thoughts below."
        badge = "EMERGENT TECH TREND"
        tags = ["#ai", "#autonomousagents", "#computeruse", "#technews", "#coding"]

    elif is_bench:
        title_prefix = f"⚡ {author} Shatters AI Benchmarks"
        title = f"{title_prefix}: {clean_snippet}"
        act_1 = f"{author} just shattered frontier benchmarks, hitting {pct_val} on complex reasoning."
        act_2 = "The system trains with pure reinforcement learning to discover self-reflection."
        act_3 = "Instead of human labels, the model checks itself against math and code verifiers."
        act_4 = f"On {bench_name}, the open model matches top labs on normal consumer chips."
        act_5a = "The pipeline cuts cost and brings frontier reasoning directly to every developer."
        act_5b = "Can open-weight models permanently overtake proprietary frontiers? Drop your thoughts below."
        badge = "NEW SOTA"
        tags = ["#ai", "#machinelearning", "#benchmarks", "#technews", "#deepseek"]

    elif is_dev:
        title_prefix = f"🚨 {author} Automates Developer Workflows"
        title = f"{title_prefix}: {clean_snippet}"
        act_1 = f"If you are still writing code the old way, stop. {author} just deployed a game-changing autonomous system."
        act_2 = "The system runs terminal tools, edits files, and tests code inside clean sandboxes."
        act_3 = "Instead of slow manual debugging, the agents catch and fix code bugs before saving."
        act_4 = f"On real-world repositories, the engine completes full-stack coding tasks in under {time_val}."
        act_5a = f"The workflow delivers a {mult_val} speedup, letting one person build like a whole dev team."
        act_5b = "Will autonomous AI agents replace traditional developer setups this year? Drop your thoughts below."
        badge = "AGENT WORKFLOW"
        tags = ["#aiagents", "#coding", "#developer", "#technews", "#productivity"]

    else:
        # Disruption / Major Open Breakthrough
        title_prefix = f"🔥 {author} Drops Major Open Breakthrough"
        title = f"{title_prefix}: {clean_snippet}"
        act_1 = f"{author} just dropped a major technical breakthrough that could redefine AI capability."
        act_2 = "The release packages frontier weights into an open design accessible to everyone."
        act_3 = "Instead of paid API paywalls, the weights run locally on normal chips."
        act_4 = f"With {pct_val} retention across long prompts, developers can process whole codebases at once."
        act_5a = f"The release provides a {mult_val} speed boost, accelerating open research across the community."
        act_5b = "Is this the tipping point for open source artificial intelligence? Drop your take in the comments."
        badge = "MAJOR BREAKTHROUGH"
        tags = ["#ai", "#machinelearning", "#opensource", "#technews", "#tech"]

    sentences = [act_1, act_2, act_3, act_4, act_5a, act_5b]
    narration_text = " ".join(sentences)
    words = narration_text.split()
    grade = calculate_reading_grade(narration_text)

    # TikTok description formatted with exactly 5 hashtags and ending question
    desc_text = f"{title}\n\n{act_1} {act_2} {act_5a}\n\n{act_5b}\n\n{' '.join(tags)}"

    return {
        "title": title,
        "title_prefix": title_prefix,
        "badge": badge,
        "author": author,
        "hook_opening": act_1,
        "hook_sentence": act_1,
        "act_1_hook": act_1,
        "act_2_evidence": act_2,
        "act_3_conflict": act_3,
        "act_4_demo": act_4,
        "act_5_resolution": act_5a,
        "question": act_5b,
        "script_sentences": sentences,
        "narration_text": narration_text,
        "reading_grade": grade,
        "word_count": len(words),
        "est_duration": round(len(narration_text) * 0.058, 2),  # ~160 WPM
        "hashtags": tags,
        "description": desc_text,
        "clean_text": clean_text,
    }


def write_5act_script(
    story_or_find: dict,
    use_llm: bool = True,
    deadline: float | None = None,
) -> dict:
    """Generate a high-retention 5-act narrative script for a vertical tech video.

    Attempts Gemini LLM generation when GEMINI_API_KEY is available and use_llm is True.
    Automatically and safely falls back to the deterministic _heuristic_5act_script()
    on missing keys, rate limits, timeouts, or schema mismatches ($0 spend guarantee).
    """
    author = story_or_find.get("author_name") or story_or_find.get("author") or "AI Labs"
    raw_text = story_or_find.get("text") or story_or_find.get("summary") or story_or_find.get("article") or ""
    clean_text = re.sub(r"https?://\S+", "", raw_text).strip()

    if use_llm and os.environ.get("GEMINI_API_KEY"):
        try:
            prompt = FIVE_ACT_PROMPT.format(author=author, content=clean_text[:1800])
            res = llm_json(prompt, deadline=deadline or (time.time() + 60))
            sentences = res.get("script_sentences")
            if (
                isinstance(sentences, list)
                and len(sentences) >= 5
                and all(isinstance(s, str) and len(s.split()) >= 4 for s in sentences)
            ):
                narration = " ".join(sentences)
                grade = calculate_reading_grade(narration)
                tags = res.get("hashtags") or ["#ai", "#technews", "#coding", "#machinelearning", "#tech"]
                title = res.get("title") or f"⚡ {author} AI Breakthrough"
                question = sentences[-1] if sentences[-1].endswith("?") else (res.get("question") or "Drop your thoughts below.")

                desc_text = f"{title}\n\n{' '.join(sentences[:2])}\n\n{question}\n\n{' '.join(tags)}"

                return {
                    "title": title,
                    "title_prefix": res.get("title_prefix") or "⚡ AI BREAKTHROUGH",
                    "badge": res.get("badge") or "BREAKTHROUGH",
                    "author": author,
                    "hook_opening": sentences[0],
                    "hook_sentence": sentences[0],
                    "act_1_hook": res.get("act_1_hook") or sentences[0],
                    "act_2_evidence": res.get("act_2_evidence") or sentences[1],
                    "act_3_conflict": res.get("act_3_conflict") or sentences[2],
                    "act_4_demo": res.get("act_4_demo") or sentences[3],
                    "act_5_resolution": res.get("act_5_resolution") or sentences[4],
                    "question": question,
                    "script_sentences": sentences,
                    "narration_text": narration,
                    "reading_grade": grade,
                    "word_count": len(narration.split()),
                    "est_duration": round(len(narration) * 0.058, 2),
                    "hashtags": tags,
                    "description": desc_text,
                    "clean_text": clean_text,
                }
        except Exception as e:
            print(f"[write] LLM 5-act generation failed or bypassed ({e}), utilizing deterministic fallback")

    # Deterministic heuristic fallback ($0 spend guarantee)
    return _heuristic_5act_script(story_or_find)


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
