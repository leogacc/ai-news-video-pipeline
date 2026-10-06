# Agent Graph — roles, contracts, prompts

Nine roles. Deterministic stages are plain Python (`pipeline/*.py`); LLM stages call Gemini free tier. Every LLM stage has a JSON contract and a veto path — a failed stage aborts the run and alerts via Telegram instead of shipping a bad video.

```
SCOUT → CURATOR → EXPLAINER → SCRIPTWRITER → FACT-CHECKER → PRODUCER → QA GATE → PUBLISHER
                                                                              ↘ ANALYST (weekly loop)
```

## 1. Scout (deterministic — `ingest.py`)
- **In:** nothing (pulls Google News RSS for AI queries; merges `input/stories_override.json` if present and fresh — that's how a hand-curated pick, e.g. from the morning digest, overrides automation).
- **Out:** `output/stories.json` — list of `{id, title, summary, url, source, published}` ranked newest-first, deduped against `state.json`.
- **Rule:** never emit a story whose id is in `seen_ids`. Dedupe key = sha1 of normalized title.

## 2. Curator (LLM)
- **In:** `stories.json` (top 12).
- **Out:** ranked pick — daily: 1 story; weekly: 5–7 stories.
- **Prompt:** "You curate AI news for a faceless video channel aimed at high-school students. Rank these stories by (1) real-world impact, (2) visual explainability, (3) novelty. Skip pure funding-round press releases unless the amount changes the industry. Return JSON: {picks: [{id, reason}]}."
- **Contract:** `{"picks": [{"id": "...", "reason": "..."}]}`. If the model returns an id not in the input, the run aborts.

## 3. Explainer (LLM)
- **In:** picked stories + source summaries.
- **Out:** plain-language brief per story a 15-year-old can follow: what happened, why it matters, one everyday analogy.
- **Prompt:** "Explain this AI news for a smart high-schooler. Rules: Flesch-Kincaid grade ≤ 9. No unexplained jargon — every technical term gets a one-line analogy first. Lead with why a teenager should care. 120–180 words. Return JSON: {brief, analogy, why_it_matters}."
- **Why separate from Scriptwriter:** keeps the simplification step inspectable and re-usable for the weekly long-form (which reuses the daily briefs).

## 4. Scriptwriter (LLM)
- **In:** Explainer briefs.
- **Out:** `output/script.json`:
```json
{
  "title": "YouTube-style title, <60 chars, no clickbait lies",
  "hook": "first spoken line, <3 seconds, curiosity gap",
  "segments": [{"text": "spoken narration", "broll": "stock footage query, 2-4 words"}],
  "description": "platform description with sources linked",
  "hashtags": ["#ai", "#ainews"]
}
```
- **Short-form prompt:** "Write a 150–300 word voiceover script from this brief. First line must hook in under 3 seconds — no intro, no 'welcome back'. One idea per segment (1–2 sentences each). Conversational, present tense. End with a follow CTA. Each segment needs a 'broll' keyword query for stock footage."
- **Long-form prompt:** "Write a 1500–2500 word script covering these briefs as chapters. Cold open with the week's biggest story in 30 seconds, then chapters with spoken transitions ('meanwhile…', 'here's why that matters…'). Recap + CTA at the end."
- **Contract:** total word count within bounds; every segment has `broll`; hook ≤ 20 words.

## 5. Fact-checker (LLM, veto power)
- **In:** `script.json` + source story texts.
- **Out:** `{"verdict": "ok|fail", "issues": [...]}`.
- **Prompt:** "You are a fact-checker. Compare every factual claim in this script against the sources. Flag anything not supported, exaggerated, or stated with false certainty (dates, numbers, model names, company claims). Return JSON. When in doubt, flag it."
- **Rule:** `fail` → run aborts, Telegram alert with the issues. No video ships on a failed check. This is the credibility firewall — non-negotiable for a news channel.

## 6. Producer (deterministic — `tts.py`, `captions.py`, `visuals.py`, `render.py`)
Four sub-steps, no LLM:
- **Voice:** Kokoro-82M (`af_sarah`, fixed for channel consistency), per-segment wavs → `narration_full.wav` + `timings.json`. ~1× real-time on 2 vCPUs.
- **Captions:** faster-whisper `base.en`, word timestamps → karaoke `.ass` (active word highlighted, rest white, middle-third placement).
- **Visuals:** Pexels API per `broll` keyword (Pixabay fallback), cached by keyword; no match → generated title card with slow Ken Burns zoom.
- **Render:** two-pass ffmpeg — per-segment 1080×1920 clips → concat → captions burned in + ducked music bed + loudnorm → H.264 MP4. Weekly: 1280×720 16:9.

## 7. QA gate (deterministic — `qa.py`, blocking)
Checks, in order; any failure blocks publishing and alerts:
1. Video duration within ±3s of narration duration.
2. Resolution matches target (1080×1920 or 1280×720), 30 fps.
3. Caption file exists, non-empty, ≥ 80% of spoken words covered.
4. Script Flesch-Kincaid grade ≤ 9.5 (the high-school requirement, enforced in code).
5. Output file > 500 KB (catches silent/blank renders).

## 8. Publisher (deterministic — `publish.py`)
- **Phase 1 (day one):** sends MP4 + title + hashtags to the Telegram review queue. You post from your phone in ~30 seconds per platform, or tap through later. Zero approvals needed.
- **Phase 2:** YouTube Data API `videos.insert` (uploads as private until OAuth verification passes; native `publishAt` scheduling — the only platform with it).
- **Phase 3:** Instagram Graph API (needs Business/Creator account + Meta app review, days) and TikTok Content Posting API (needs content audit, weeks) — run both applications in parallel while Phase 1 ships daily.
- **Rule:** one publisher per platform, dedupe key = story id — a retry can never double-post.

## 9. Analyst (weekly, LLM-assisted)
- **In:** YouTube Analytics API (views, retention) — phase 2+.
- **Out:** topic scores appended to `state.json` (`topic_affinity: {topic: score}`).
- **Loop:** Curator's prompt gets the top/bottom 3 topics injected ("your audience retained 2× longer on robotics stories; deprioritize funding news") — the graph learns what the audience actually watches.

## Failure policy
- Any stage exception → run aborts → Telegram alert with stage name + error tail. Nothing partial ever publishes.
- Retries: network calls (Pexels, Gemini) retry 3× with backoff; ffmpeg failures do not retry (deterministic — alert instead).
- Idempotency: `state.json` is only updated after QA passes; a re-run never re-emits a shipped story.
