# AI News Video Pipeline

Hands-off pipeline that turns AI news into a daily short-form video (TikTok / Reels / YouTube Shorts) and a weekly long-form video (YouTube). Everything runs on free infrastructure; every script is written so a high-schooler can follow the content.

## The 3 big decisions

| Decision | Choice | Why |
|---|---|---|
| **Host** | GitHub Actions (public repo), scheduled workflows | More hands-off than a VM: no patching, no idle-reclamation, no credit card, unlimited Linux minutes on public repos. Fallback: Oracle Cloud Always Free (2 OCPU / 12 GB ARM, free forever) runs the same scripts unchanged if you ever want a real VM. |
| **Video stack** | Kokoro TTS + faster-whisper karaoke captions + Pexels/Pixabay b-roll + raw ffmpeg | $0, commercial-clean licenses (Apache-2.0 / MIT / LGPL + stock content licenses), runs on 2 vCPUs. A 60s short renders in ~5–10 min end-to-end. |
| **Publishing** | Phase 1: Telegram review queue. Phase 2: YouTube Data API, then IG Reels, then TikTok | TikTok needs a 2–6 week content audit and IG needs Meta app review before auto-posting works. The Telegram queue ships day one with zero approvals and doubles as the safety net forever. |

## How it flows

```
cron (daily 06:00 PT)                    cron (weekly, Sun 06:00 PT)
  │                                        │
  ▼                                        ▼
SCOUT ──► CURATOR ──► EXPLAINER ──► SCRIPTWRITER ──► FACT-CHECKER ──► PRODUCER ──► QA GATE ──► PUBLISHER
(fetch     (pick 1       (high-school     (hook-first      (veto power:      (TTS + captions    (duration,     (Telegram queue
 news,      story /        level rewrite,   short / chapters  claims must       + b-roll +        safe zones,   → you tap post;
 dedupe)    5–7 weekly)    grade ≤ 9)        long scripts)     match sources)    ffmpeg render)    captions)      YT API phase 2)
                                                                                                              │
                                                                                                              ▼
                                                                                                           ANALYST (weekly:
                                                                                                           views → topic scores
                                                                                                           feed back to Curator)
```

Full role contracts and prompts: [`AGENT_GRAPH.md`](AGENT_GRAPH.md).

## Cost

$0/month. Optional: X API pay-per-use (~$1/mo at this volume) if you add X later. No credit card required for anything in Phase 1. If you ever use an aggregator to skip TikTok/IG audits, that's ~$20/mo (Metricool) — not needed to start.

## Setup (one-time, ~1 hour)

1. Create a **public** GitHub repo, push this folder. (Private also works: 2,000 min/mo free, this workload uses ~900–1,400.)
2. Add repo secrets (Settings → Secrets → Actions):
   - `GEMINI_API_KEY` — free tier at Google AI Studio, drives Curator/Explainer/Scriptwriter/Fact-checker
   - `PEXELS_API_KEY` — free at pexels.com/api (200 req/hr, plenty)
   - `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — BotFather + your chat; this is the review queue and failure alerts
   - Phase 2 only: `YOUTUBE_CLIENT_SECRETS` (OAuth client JSON, base64)
3. Drop 2–3 royalty-free music tracks (Pixabay Music / Mixkit) into `pipeline/assets/music/`.
4. Run "daily-short" manually once from the Actions tab (workflow_dispatch) to verify.

After that: daily short renders ~06:00 PT and lands in your Telegram. Weekly long-form renders Sunday 06:00 PT. Failure alerts go to the same Telegram chat.

## Repo layout

```
pipeline/
  config.yaml        # all knobs: voices, formats, word counts, thresholds
  run.py             # orchestrator: runs every stage in order, alerts on failure
  ingest.py          # Scout: Google News RSS + override file, dedupe → stories.json
  write.py           # Curator + Explainer + Scriptwriter + Fact-checker (Gemini)
  tts.py             # Producer (audio): Kokoro TTS per segment → narration_full.wav
  captions.py        # Producer (captions): faster-whisper → karaoke .ass
  visuals.py         # Producer (visuals): Pexels/Pixabay b-roll cache, title-card fallback
  render.py          # Producer (render): two-pass ffmpeg → final mp4
  qa.py              # QA gate: duration, resolution, caption sanity, grade-level check
  publish.py         # Publisher: Telegram review queue (+ YouTube API, phase 2)
  state.json         # seen/posted story ids — committed back each run (also defeats
                     # GitHub's 60-day schedule auto-disable)
  output/            # mp4s, scripts, captions per run (uploaded as Actions artifacts)
  cache/clips/       # downloaded b-roll, keyed by keyword (persist via actions/cache)
  assets/music/      # your royalty-free tracks
.github/workflows/
  daily.yml          # 06:00 PT daily short
  weekly.yml         # Sunday 06:00 PT long-form
```

## Notes & gotchas

- **One 1080×1920 master** covers TikTok, Reels, and Shorts — no per-platform re-render.
- **Captions go in the middle third** (Alignment 5), never the bottom: platform UI covers the bottom ~20–35%.
- **Commercial-clean only**: Kokoro (Apache-2.0), faster-whisper (MIT), ffmpeg (LGPL), Pexels/Pixabay content licenses, Pixabay/Mixkit music. Do not swap in Coqui XTTS (non-commercial) or edge-tts (ToS gray zone) on a monetized channel.
- **Whisper jargon**: AI news is full of model names; `base.en` minimum, `--language en` forced, initial prompt seeded with expected terms.
- **GitHub schedule delays**: cron runs can slip 10–30 min at peak; harmless here.
- **YouTube uploads via API start as private** until your OAuth app passes Google verification — by design, use the Telegram queue until then.
- **TikTok audit / IG app review** are the only human-speed gates in the whole system; everything else is same-day.
