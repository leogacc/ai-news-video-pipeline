# AI News Video Pipeline

A pipeline that turns the day's AI news into a short-form video every morning. Five stories, about two minutes, rendered in a terminal aesthetic — neon green typewriter text on black — and delivered to a Telegram review queue.

## What it produces

A daily 9:16 video (TikTok / Reels / Shorts format):

- **Cold open** — the date and the five stories, typed out letter-by-letter in a terminal intro with a red `BREAKING` kicker
- **Headline hooks** — five rapid headline cuts, each pairing a verified photo of the story's key person with the company logo
- **Deep dives** — each story gets 2–3 shots: real photos, article screenshots, or animated data graphics, with a persistent `#1`–`#5` story badge
- **Captions** — per-letter typewriter captions synced to true TTS word timings, with a trailing block cursor

Stories are ordered most-interesting-first. Narration is Kokoro TTS (`am_echo`, 1.10x). Every script is gated at Flesch-Kincaid grade ≤ 9.5.

## How it works

```
03:00 PT  X/news scan ──► x_curated.json
03:45 PT  curate + write script (5 stories, deduped against state.json)
             │
             ▼
          TTS ──► captions ──► visuals ──► render ──► QA gate ──► Telegram
        (Kokoro)   (word-timed)  (verified)  (ffmpeg)   (blocking)
```

The 03:45 run is an agent that acts as scout, curator, writer, and fact-checker — it picks the stories, writes the script, and eye-verifies every visual before the mechanical stages run. The VM executes only the deterministic stages: TTS, captions, visual assembly, render, QA, publish.

**Visual sourcing policy:** every evidence shot is verified by eye before it ships. Named people get real photos, companies get real logos or buildings, documents get the actual article. No stock or Wikimedia Commons for evidence shots — stock is illustrative b-roll only. Anything unverifiable falls back to a screenshot of the specific source passage; a black frame is treated as a failed shot, never shipped as fine.

**Versioning:** every pipeline change bumps `pipeline/VERSION` and gets a `CHANGELOG.md` entry. Each render stamps its pipeline version into `qa.json`, so any video can be traced to the exact code that built it.

## Setup

**Requirements:** Python 3.12, ffmpeg, ~8 GB RAM. The daily run currently executes on a VM (see `run_vm.sh`); GitHub Actions workflows are kept as fallback with their schedules disabled.

1. Clone the repo and create a Python 3.12 venv:
   ```
   python3.12 -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
   .venv/bin/pip install -r pipeline/requirements-vm.txt   # VM-only pins
   ```
2. Copy your secrets into `.env` (never committed — it's in `.gitignore`):
   ```
   PIXABAY_API_KEY=...        # illustrative b-roll only
   TELEGRAM_BOT_TOKEN=...     # review queue + failure alerts
   TELEGRAM_CHAT_ID=...
   ```
3. Run the mechanical stages:
   ```
   ./run_vm.sh daily
   ```
   This runs TTS → captions → visuals → render → QA → publish. The QA gate blocks publishing on any failure.

For the full scheduled flow (scan + agent curation + render), see the runbook in `pipeline/` — the 03:00/03:45 crons orchestrate it.

## Configuration

All knobs live in `pipeline/config.yaml`: TTS voice/speed, caption style, shot geometry, QA thresholds. Story state (dedupe) lives in `pipeline/state.json`.

## Project structure

```
pipeline/
  run.py            # orchestrator: stages in order, alerts on failure
  ingest.py         # news fetching + dedupe
  tts.py            # Kokoro TTS with true word timings + fingerprint cache
  captions.py       # per-letter typewriter captions
  visuals.py        # visual sourcing: verified pins → story media → screenshots
  analytics.py      # terminal-style animated data graphics
  render.py         # two-pass ffmpeg render
  qa.py             # blocking QA gate
  publish.py        # Telegram review queue
  selfplug.py       # character-emotion montage from the intro portrait
  config.yaml       # all tunables
  VERSION           # current pipeline version
  CHANGELOG.md      # version history
.github/workflows/
  daily.yml         # fallback: daily short via Actions (schedule disabled)
  weekly.yml        # fallback: weekly long-form via Actions (schedule disabled)
```

## Roadmap

**Phase 1 — Daily shorts (live).** The current system: scan, write, render, QA, Telegram delivery every morning.

**Phase 2 — TikTok publishing.** Browser automation on tiktok.com/upload (the official API can't attach sounds). Flow: pipeline drafts the post (video + description + hashtags + rotated saved song) → Telegram "Approve & Post" → posts only on approval. Pending: one-time login and the saved-songs list.

**Phase 3 — Weekly long-form.** A 16:9 weekly digest for YouTube. Deferred until the daily format is locked.

**Phase 4 — Native publishing.** YouTube Data API and Instagram Graph API once their reviews/audits clear, replacing the manual Telegram step.

**Phase 5 — Feedback loop.** View and retention analytics feeding back into story selection — topics that hold attention get weighted up in curation.

**Open questions:** background music (currently no music by design — the terminal aesthetic carries it); multi-language narration.

## License notes

The stack is commercial-clean: Kokoro (Apache-2.0), faster-whisper (MIT), ffmpeg (LGPL), Pixabay content license for b-roll. Keep it that way — don't swap in non-commercial TTS models on a monetized channel.
