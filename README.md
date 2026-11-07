# AI News Video Pipeline

Turns AI news into short vertical videos, and clips the single most interesting AI find four times a day.
Pipeline version **2026.11.06.9** (`pipeline/VERSION`, 2026-11-06). Repo: `github.com/leogacc/ai-news-video-pipeline`.

This README is the handover for an agent taking over operations. It states the current state first, then how to run things.
The live rules are in `scout/README.md`, `templates/clips/template.yaml`, `docs/ROADMAP.md`, and `REPORT.md` (TikTok growth blueprint) — read those in full before touching anything.
`pipeline/CHANGELOG.md` tracks all versions and verified fixes.
`AGENT_GRAPH.md` is design background only; its schedule, voice, and LLM-stage descriptions are outdated — do not run from it.

## READ THIS FIRST — current state (2026-11-06)

The pipeline is fully cut over to the automated Free X Search and Remotion animation architecture. Threads has been decommissioned and archived in `archive/threads/`.
The 4x-daily scout crons run automatically via `scout/x_scout.py --run-cron`. Paused jobs remain disabled.

| Job | Schedule (PT) | Status |
|---|---|---|
| `x-scout-finds-7am` | 07:00 | RUNNING (`scout/x_scout.py --run-cron`) |
| `x-scout-releases-rumors` | 11:00 | RUNNING (`scout/x_scout.py --run-cron`) |
| `x-scout-finds-4pm` | 16:00 | RUNNING (`scout/x_scout.py --run-cron`) |
| `x-scout-finds-7pm` | 19:00 | RUNNING (`scout/x_scout.py --run-cron`) |
| `muse-video-pipeline-daily` (daily video) | 18:00 | DISABLED |
| `x-news-daily-scan` (daily X scan) | 17:00 | DISABLED |
| `pipeline-fix-until-video-lands` (watchdog) | every 2h | DISABLED |
| `rumors-digest-daily-6am` | 06:00 | DISABLED |
| `daily-ai-news-digest` (text digest) | 11:00 | DISABLED |
| `meal-log-evening-nudge` | 21:53 | DISABLED |

The four scout jobs share one body and the same state files; each run re-checks dedupe and evaluates posts through the **TikTok Worthiness Scorecard** ($\ge 28/40$, no pillar $< 6$). Runs with zero passing candidates exit silently without publishing.
Job definitions live in `crons/` (one file per job, `enabled: false` on the paused ones). The primary production workflow is driven by `scout/x_scout.py --run-cron`.
The weekly 16:9 long-form is deferred until the daily format is locked — do not start it.

The user is the creative director. They watch every render and reply with frame-by-frame corrections, often timestamped.
When they correct something, fix it at the pipeline level (code or template rule), version it, rebuild the latest clip, and push the new version to Telegram.
Never defend a previous version and never re-push a superseded one. A render only counts as done once it is in the Telegram review queue.

## What it produces

A narrated finds clip: 1080x1920, 9:16, 30 fps, H.264 High L4.0, yuv420p, faststart, about −14 LUFS.
Narration is Kokoro `am_echo` at 1.20x (`pipeline/config.yaml`). Captions are terminal green (`#39FF14`) per-letter typewriter with a trailing block cursor, top-anchored.
Every newly written title, bio, and description is gated at Flesch-Kincaid grade ≤ 9.5. Music is OFF in renders — the music bed is preserved as
`pipeline/assets/music/ai_digest_bed.mp3.disabled`; never re-enable it or add a copyrighted song unprompted.
The daily digest (5 stories, same format, most-interesting-first) is PAUSED with the shutdown above; its code and templates stay in the repo.

## The operator loop (scout)

One automated run, in order (executed via `scout/x_scout.py --run-cron`):

1. **Scout** the VIP accounts in `scout/accounts.yaml` and keyword queries in `scout/keywords.yaml` using Free X Search (`pipeline/x_search.py` via Twitter Syndication API, Google News RSS fallback, and Hacker News dispatches). Threads has been decommissioned and archived in `archive/threads/`.
2. **Classify** each notable post as RELEASE (official announcement), RUMOR (unconfirmed/leak), or FIND (general AI find — tools, demos, projects, research, benchmarks). Skip hype, memes, and engagement bait, and log why.
3. **Save everything first** to `scout/saved_items.json` (post_id, author, date, text, url, category, source, verified link). Rumors are saved only. Releases are part of finds: a release is picked and clipped exactly like a find, labelled FIND.
4. **Evaluate via TikTok Worthiness Scorecard (`scout/x_scout.py:excitement_gate_score`)**:
   - **Tier 1 Hard Disqualifiers**: Immediate rejection (0/40) for routine plugins/integrations, minor hardware spec bumps without AI shifts, legal/lawsuit disputes, and routine bugfixes.
   - **Tier 2 4-Pillar Rubric**: Evaluated on Hook Strength (0-10), Educational Value (0-10), Relatable Stakes (0-10), and Visual Potential (0-10; benchmark/paper finds receive an 8/10 baseline due to Remotion animations).
   - **Passing Threshold**: Total $\ge 28 / 40$, with no single pillar $< 6 / 10$.
   - **Silent Exit**: If zero candidates clear the bar, terminate cleanly with exit code 0 without sending Telegram messages.
5. **Dedupe** before building: `scout/state.json` (seen/posted ids), `scout/clipped_finds.json`, and `pipeline/state.json` posted ids. A clipped or posted item is never rebuilt except for substantive new developments (major version release, materially changed capability/benchmark).
6. **Build the clip** declaratively via `pipeline/assemble.py` per `templates/clips/template.yaml` (Dynamic Hug overlays, Kokoro TTS `am_echo` 1.20x, ASS typewriter captions, -14 LUFS loudnorm).
7. **Automated QA Gate**: Verified through `pipeline/qa.py --clip`. A clip must strictly satisfy all checks (1080x1920, 30fps, H.264 High L4.0, faststart, audio sync & loudness, top-anchored safe area captions, edge-slice check on verification stills) or assembly aborts.
8. **Publish** to Telegram review queue (`pipeline/publish.py` -> `@aividpipBOT`). Reports to the user only when a verified clip lands. No-clip runs stay completely silent.

## Quickstart

```bash
# 1. Bootstrap environment (Python 3.12, Kokoro weights, Node/Remotion, .env)
./setup_env.sh

# 2. Run automated cloud crons scout cycle (dry-run or live)
.venv/bin/python3 scout/x_scout.py --run-cron --dry-run
.venv/bin/python3 scout/x_scout.py --run-cron

# 3. Run automated QA gate on any rendered clip
.venv/bin/python3 pipeline/qa.py --clip pipeline/output/scout/clips/sample_paper_find

# 4. Run the full unit regression test suite (41 tests)
.venv/bin/python3 -m unittest scout/test_cron_runner.py scout/test_scorecard.py pipeline/test_assemble.py pipeline/test_animations.py pipeline/test_x_search.py pipeline/test_tweet_card.py pipeline/test_qa_clip.py
```

## Repo layout

```
pipeline/            # Core processing engine
  x_search.py        # Free X Search engine (Syndication API + Google News RSS + Algolia)
  tweet_card.py      # Dark-mode 2x official post renderer (Syndication + Chromium)
  animations.py      # Remotion integration wrapper (BenchmarkLadder, ArchitectureDiagram, KineticMetricCounter)
  animations/        # Remotion React/TypeScript compositions root
  assemble.py        # Declarative clip assembler (Dynamic Hug video overlays, Kokoro TTS, ASS captions, loudnorm)
  qa.py              # Automated Clip QA Gate (--clip <dir>, enforces 1080x1920, 30fps, H.264 High L4.0, loudnorm, captions, pin_edge)
  clip_frames.py     # Shared Dynamic Hug frame builder and transparent video overlay generator
  tts.py             # Kokoro TTS (am_echo 1.20x), token-level timestamps, sanitized proxy handling
  captions.py        # Per-letter typewriter ASS caption generator (neon green #39FF14, top-anchored MarginV >= 1400)
  publish.py         # Telegram review queue dispatcher (@aividpipBOT)
  pin_edge_check.py  # OCR / slice detector ensuring no truncated headline ascenders/descenders
  config.yaml        # Pipeline tunables (voice, geometry, loudness, safe areas)
  VERSION            # Single-line semantic version (2026.11.06.8)
  CHANGELOG.md       # Chronological version changelog
scout/               # Discovery & Curation
  x_scout.py         # Automated cloud crons runner (--run-cron), 4-pillar scorecard, Telegram delivery
  accounts.yaml      # VIP X accounts to monitor (OpenAI, DeepSeek, Anthropic, leaders)
  keywords.yaml      # High-signal discovery queries
  saved_items.json   # Central saved pool
  state.json         # Deduplication tracking (seen IDs, run timestamps)
  clipped_finds.json # History of assembled and published clips
crons/               # Scheduled Cloud Crons definitions (4x daily: 07:00, 11:00, 16:00, 19:00 PT)
archive/             # Decommissioned components
  threads/           # Archived Threads crawler (threads_media.py, threads.yaml)
setup_env.sh         # Hermetic environment bootstrapper
```

## Setup

1. Run `./setup_env.sh` to initialize Python venv, install PyTorch (CPU-only), Kokoro TTS offline weights cache, Node/Remotion dependencies, and verify system binaries (`ffmpeg`, `node`, `npm`).
2. Populate `.env` (`chmod 0600 .env`):
   - `TELEGRAM_BOT_TOKEN=...` (Bot token for `@aividpipBOT`)
   - `TELEGRAM_CHAT_ID=1904835992` (Review queue chat ID)
   - `PIXABAY_API_KEY=...` (Illustrative b-roll fallback)
3. Ensure `ffmpeg` and `node >= 18` are on `PATH`.

## Declarative Clip Assembly

Every clip is assembled declaratively via `pipeline/assemble.py`:

```python
from pipeline.assemble import assemble_clip

spec = {
    "title": ["DEEPSEEK-R1", "REASONING MODEL"],
    "bio": "Source: DeepSeek AI, Jan 2025",
    "script": "DeepSeek just open-sourced R1, rivaling OpenAI o1 at a fraction of the cost.",
    "shots": [
        {"type": "tweet_card", "tweet_id": "1882627116931752146", "duration": 5.5},
        {
            "type": "animation",
            "composition": "BenchmarkLadder",
            "props": {
                "headline": "AIME 2024 Math Accuracy",
                "items": [
                    {"label": "DeepSeek-R1", "score": 79.8, "highlight": True},
                    {"label": "OpenAI o1-preview", "score": 79.2, "highlight": False},
                ],
                "benchmark_max": 100
            },
            "duration": 8.0
        }
    ]
}

assemble_clip(spec, output_dir="pipeline/output/scout/clips/my_clip")
```

The assembler automatically:
1. Synthesizes Kokoro voiceover (`am_echo` 1.20x) with token-level timestamps.
2. Generates Remotion video cutaways and Dynamic Hug overlays.
3. Concat-filters all shots seamlessly with hard cuts.
4. Normalizes audio to -14 LUFS (`loudnorm=I=-14:LRA=11:TP=-1.0`).
5. Burns top-anchored `#39FF14` neon green typewriter captions.
6. Executes the strictly blocking **Automated QA Gate** (`pipeline/qa.py --clip`).

Source-video clips (the source has usable audio/video) follow the same declarative specification with `"type": "video"`, preserving source audio or compositing narration with Dynamic Hug transparent overlays.

## Rebuild a clip as v2 / v3

When the user corrects a clip, rebuild it as a new version — never edit the published file in place:

1. Preserve the outgoing version first: `clip.mp4` → `clip_vN.mp4`, `meta.json` → `meta_vN.json`, `frame_*.png` → `frame_*_vN.png`, `captions.ass` → `captions_vN.ass`.
2. Change only what the user asked for (frames, or narration, or both). Re-run `render.py` (captions must come out byte-identical when the narration is unchanged — assert the md5), then `assemble.py` (narration re-derived deterministically, so final LUFS/TP must match the previous version), then `finalize.py`.
3. Set `meta.json` `version` to the new number and add a `vN_changes` field saying what changed.
4. Push the new version to Telegram with a "SUPERSEDES vN" caption. The old version stays in Telegram — it cannot be unsent.

## Pipeline upgrade (versioned flow)

Fixes land at the pipeline level, never as quick detail fixes on one render. Full flow: `skills/local-pipeline-upgrade/SKILL.md`. Short version:

1. Implement the change in the right layer (code in `pipeline/`, worker instructions via the scheduler, templates in `templates/`). Find the root cause; do not patch one render.
2. Verify it works — run the affected stage or a full render.
3. Bump `pipeline/VERSION` (one line, `YYYY.MM.DD.N`, N increments within a day).
4. Append `pipeline/CHANGELOG.md`, newest entry first: version, date, what changed and why, in plain mechanics.
5. If worker instructions changed: update via the scheduler's update path with the complete revised body, then verify the saved definition contains the new text. Never edit a job file directly and stop there — the scheduler ignores file edits.
6. Confirm the version stamp: `run.py` prints the pipeline version and stamps `pipeline_version` into `qa.json`. Check it.
7. Report the new version number + what changed, in one short message.

## Publish to Telegram

`pipeline/publish.py`: `telegram_send(video: Path, caption: str)` sends the clip (caption truncated to 1024 chars, HTML parse mode); `telegram_send_description(script: dict)` sends the description built from the script's `description` + `hashtags` fields. Both load `.env` first. The description must say "find" (releases are part of finds), and for a major-progress re-clip it must say "update" and what is new. The Telegram description still says "FIND:" even though the on-screen bio no longer does (see below).

## Rules that govern every build

Summaries only — the template file is the authority. Read `templates/clips/template.yaml` in full before building.

- **Vision-crop every evidence shot by eye.** Articles: kicker + complete headline + dek + byline, no site chrome. X posts: exactly one post, avatar through action bar. Leave clear whitespace beyond the outermost text line — a sliced ascender/descender is a failed pin (`pipeline/pin_edge_check.py` blocks it in QA). Never pin a login wall, verification/CAPTCHA page, paywall, or adblock modal. No Commons or stock for evidence shots — stock is illustrative generic-action b-roll only, with literal visible queries, never metaphors.
- **Dynamic hug** (`pipeline/clip_frames.py`): on narrated clips the title and bio boxes hug the mid content per shot — title box directly above the content, bio box directly below it (20px box gaps; white-text-to-content gaps 40px title / 36px bio). Content itself does not move (centred y375..1325, max 960 wide, clean black). Hard limits: title top ≥ y130, bio bottom ≤ y1500.
- **No blur background**: never a blurred background behind mid content. The content zone stays clean black; content is scaled down (max 960 wide) so it carries black side padding.
- **Bio is the Source line only**: the on-screen bio is a single regular-weight line, `Source: <root>, <date>`. The root source is the company announcement, official blog, repo, paper, or product page — NEVER the X/Threads post that surfaced it. A via-handle bio FAILS QA. The Telegram description may still name the surfacing post as its source link.
- **Watermark**: `@leos.logos` directly beneath the bio/source block on every clip frame — x=60, bio bottom + 20px, clamped so its bottom never passes y1495 — 80% transparent (20% opaque, alpha 51). It may overlap the mid content.
- **Block style**: title and bio text WHITE, both blocks 50% transparent black, blurred, feathered edge — never a hard opaque panel. Captions stay terminal green.
- **Captions**: terminal green per-letter typewriter, trailing block cursor, TOP-ANCHORED (ASS alignment 7, one fixed style MarginV) — first glyph row ~1530 on every frame. Line breaks are deferred to the next line's first letter (never a cursor-only line). No new captions when burnt-in subtitles are present.
- **TTS delivery guarantees** (`pipeline/tts.py`, v2026.11.05.1): segment-initial words get a disposable warm-up word ("Well,") absorbing Kokoro's soft onset, then trimmed — first words attack cleanly. After every comma lacking a ≥0.15s pause, 0.22s of silence is spliced in; the pause detector measures only silence after the word ends. Regression tests: `pipeline/test_tts.py`.
- **Footage priority**: (1) source/company explaining on video, with its own audio, as the backbone; (2) other useful footage as cutaways; (3) Remotion motion graphics (`BenchmarkLadder`, `ArchitectureDiagram`, `KineticMetricCounter`) for abstract finds, benchmark comparisons, and research papers; (4) vision-cropped root-source stills only when no video exists; (5) narration last. NEVER a third-party surfacing post as a visual. No pure-text shots.
- **No mid-screen text without an analytical chart.** Visuals change exactly when the narration's subject changes; an evidence shot never shows its subject before the subject is named.
- **QA bar**: no black frames, no file that fails ffprobe, no verification walls or popups, headlines fully in frame. A render only counts as done once it passes `pipeline/qa.py --clip` and is delivered to the Telegram review queue.

## What's paused / do not touch

- The six disabled jobs in the table above. Re-enable only on the user's word.
- Weekly 16:9 long-form (`run.py --mode weekly`, `.github/workflows/weekly.yml`) — deferred.
- TikTok "approved" auto-upload: paused (login hit a puzzle/CAPTCHA in 2026-10-26; manual uploads resumed; no reply watcher exists). Do not retry the login unprompted.
- The `landscape-layout` branch — parked. X login and TikTok login — do not push either unprompted.
- Canva duplicate intro-portrait designs (23 awaiting manual deletion) — not part of this repo.

## What's not in the repo

- `.env` (secrets — see Setup). Never commit it, never print its values.
- `.venv/` and `.kokoro_cache/` (Python env + model caches).
- `pipeline/cache/` and `pipeline/output/` (local cache and rendered videos — regenerable; excluded by `.gitignore`).
- `scout/runs/` (per-run reports and raw JSONs — local logs).
- The scheduler's live job copies (under the goal workspace, `~/workspace/goals/ai-news-video-pipeline/crons/daily/`) — keep `crons/` in sync with them.
- The user's TikTok saved songs and Telegram review queue history — they live on those platforms, not here.

## Known limits and traps

- Free X Search utilizes public Twitter Syndication endpoints, Google News RSS (`site:x.com`), and Algolia HN dispatches. When Syndication is temporarily rate-limited, the system automatically falls back to Google News RSS search.
- Remotion renders require headless Chromium. Ensure Node dependencies are installed via `./setup_env.sh`.
- The VM is memory-constrained (~500MB real headroom, no swap); renders are single-flight. `run.py` hands off to `render.py` as a separate process — killing the wrapper does not stop the render; kill `render.py` itself plus orphaned ffmpeg children, then verify `ps` is clean.
- `/tmp` is small and cleaned between turns — keep anything needed under `~/workspace/`, and keep source media inside the clip folder.
- `AGENT_GRAPH.md` is stale background (see the note at the top). The daily-digest rules in the old root README (cold open, person photos as hook heroes, 1.10x voice) are superseded — this file replaces that README as the handover.
