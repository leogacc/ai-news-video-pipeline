# AI News Video Pipeline

Turns AI news into short vertical videos, and clips the single most interesting AI find four times a day.
Pipeline version **2026.11.05.7** (`pipeline/VERSION`, 2026-11-05). Repo: `github.com/leogacc/ai-news-video-pipeline`.

This README is the handover for an agent taking over operations. It states the current state first, then how to run things.
The live rules are in `scout/README.md`, `templates/clips/template.yaml`, and `pipeline/CHANGELOG.md` — read those in full before touching anything.
`AGENT_GRAPH.md` is design background only; its schedule, voice, and LLM-stage descriptions are outdated — do not run from it.

## READ THIS FIRST — current state (2026-11-05)

The user shut down everything except the finds scout on 2026-10-28. **Do not restart the paused jobs.**
They are disabled, not deleted, and return only on the user's word.

| Job | Schedule (PT) | Status |
|---|---|---|
| `x-scout-finds-7am` | 07:00 | RUNNING |
| `x-scout-releases-rumors` | 11:00 | RUNNING |
| `x-scout-finds-4pm` | 16:00 | RUNNING |
| `x-scout-finds-7pm` | 19:00 | RUNNING |
| `muse-video-pipeline-daily` (daily video) | 18:00 | DISABLED |
| `x-news-daily-scan` (daily X scan) | 17:00 | DISABLED |
| `pipeline-fix-until-video-lands` (watchdog) | every 2h | DISABLED |
| `rumors-digest-daily-6am` | 06:00 | DISABLED |
| `daily-ai-news-digest` (text digest) | 11:00 | DISABLED |
| `meal-log-evening-nudge` | 21:53 | DISABLED |

The four scout jobs share one body and the same state files; each run re-checks dedupe before picking.
Job definitions live in `crons/` (one file per job, `enabled: false` on the paused ones). The only live work right now is the scout loop below.
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

One run, in order (full rules: `scout/README.md`, job bodies in `crons/`):

1. **Scout** the accounts in `scout/accounts.yaml`, the combined queries in `scout/keywords.yaml` (X and Threads, back up to 3 months), and the Threads accounts in `scout/threads.yaml`. Never scout an account that is not listed. Never guess accounts.
2. **Classify** each notable post as RELEASE (official announcement), RUMOR (unconfirmed/leak), or FIND (general AI find — tools, demos, projects, research, benchmarks; never the "Hacks" label, and never hack-specific terms as primary search terms). Skip hype, memes, and engagement bait, and log why.
3. **Save everything first** to `scout/saved_items.json` (post_id, author, date, text, url, category, source, verified link). Rumors are saved only — the rumors digest handles them, and it is paused. Releases are part of finds: a release is picked and clipped exactly like a find, labelled FIND.
4. **Pick at most ONE top find or release.** Rank by what is most interesting, pressing, exciting, or important for the AVERAGE INTERESTED PERSON — broad appeal beats a technically neat but narrow find. Recency is only a tie-breaker. If nothing clears the bar, build nothing and end silently (state and saved pool only).
5. **Dedupe** before building: `scout/state.json` (seen/posted ids), `scout/clipped_finds.json`, and `pipeline/state.json` posted ids. A clipped or posted item is never rebuilt — except the major-progress exception: a substantive new development (new major version or official release, materially changed capability or benchmark, confirmation that changes the story — not a repost, an engagement bump, or a minor bugfix). A major-progress re-clip is labelled as an update in its description ("Update on X — previously clipped on <date>"), says what is new, and is appended to `scout/clipped_finds.json` as an update entry against the original post_id.
6. **Build the clip** per `templates/clips/template.yaml` (below).
7. **Publish** to Telegram (below). **Report** to the user only when a clip lands: the find, why it topped the run, the clip, its source, and what was skipped and why. No-clip runs stay silent.
8. **Concurrency:** never leave multiple runs in flight; never build while another scout run or the daily pipeline is rendering. If another run is rendering, do a save-only pass (steps 1–3 and 5).

State as of 2026-11-05: `scout/saved_items.json` 331 items, `scout/clipped_finds.json` 42 entries, `scout/state.json` seen_post_ids 315, posted_find_ids 42.

### The excitement gate

"Exciting" is a GATE, not a ranking factor (`scout/README.md`). A top pick must be genuinely exciting for the average interested person — surprising, big, first-of-its-kind, high-stakes, or viscerally interesting. These do NOT clear it, no matter how recent or well-sourced:

- Routine / incremental stories, including "company X adds Y support". Named example: 2026-10-27 ChatGPT iCloud Mail/Calendar plugins.
- Product and hardware launches, even first-in-category with a polished demo. Named example: 2026-10-28 XREAL Aura XR glasses. First-in-category is not exciting on its own; the bar needs a surprising capability, an unexpected crossover, or stakes beyond the product.
- Legal-dispute stories, on scale or stakes alone. Named example: 2026-11-02 NYT v Brave lawsuit.

If the pool's best is merely interesting, build nothing, end silently, and log the skip with reason "not exciting".

Note: the 2026-10-17 "no Gemini alerts" withdrawal covers personal alert pings ONLY. Gemini finds and releases stay eligible for clips — never skip a Gemini item on the alerts basis.

## Repo layout

```
pipeline/            # the code
  run.py             # orchestrator (daily/weekly modes; --skip ingest,write)
  render.py          # frame + caption generation (PIL frames, .ass captions)
  tts.py             # Kokoro TTS, word timings, delivery guarantees, fingerprint cache
  captions.py        # per-letter typewriter captions (.ass)
  clip_frames.py     # shared narrated-clip frame builder (dynamic hug, watermark)
  publish.py         # Telegram review queue
  visuals.py         # visual sourcing: verified pins, screenshots, stock b-roll
  threads_media.py   # Threads post media extraction (see traps below)
  selfplug.py        # branding / follow-CTA montage (daily, paused)
  qa.py              # blocking QA gate
  ingest.py write.py # daily scan + script writing (paused)
  analytics.py beats.py pin_edge_check.py test_tts.py tweet_card.py
  config.yaml        # tunables (voice, speed, geometry, QA thresholds)
  VERSION            # current pipeline version, one line (YYYY.MM.DD.N)
  CHANGELOG.md       # version history, newest first
  state.json         # daily dedupe log
  requirements.txt   # Python deps (torch is installed separately, CPU-only)
  assets/            # music bed (.disabled) — never re-enable it
  cache/ output/     # local-only working cache and renders — regenerable, not in the repo
templates/
  clips/template.yaml         # THE clip template — read in full before any clip build
  daily-digest/template.yaml  # daily digest template (paused)
  montage-edit/template.yaml  # portrait montage grammar (manual edits, not scout picks)
  rumors-digest/template.yaml # rumors digest template (paused)
scout/
  README.md           # scout runbook — read in full before any scout run
  accounts.yaml       # X accounts to scout (never guess others)
  keywords.yaml       # combined search queries (X + Threads)
  threads.yaml        # Threads accounts to scout
  saved_items.json    # central saved pool — ALL pipelines read this first
  state.json          # seen/posted ids, seen Threads permalinks, last run
  clipped_finds.json  # one entry per clipped find (+ update entries)
  runs/ threads_footage/  # per-run reports (local-only, not in the repo); media pulled by threads_media.py
skills/               # local motion/video skills (read before touching renders)
  local-pipeline-upgrade/SKILL.md  # the versioned upgrade flow (below)
  local-motion-language/SKILL.md   # channel motion personality + tokens
  local-shot-grammar/SKILL.md      # shot-selection grammar (literal visuals)
  local-short-form-video/SKILL.md  # vertical short-form grammar
  local-explainer-video/SKILL.md   # script -> storyboard -> render
  local-animated-data-visualization/SKILL.md  # + other local-* motion skills
crons/                # scheduled-job definitions (one file per job)
  x-scout-finds-7am, x-scout-releases-rumors (11:00), x-scout-finds-4pm, x-scout-finds-7pm
  muse-video-pipeline-daily, x-news-daily-scan, rumors-digest-daily-6am, daily-ai-news-digest  # DISABLED, preserved
.github/workflows/
  daily.yml weekly.yml  # GitHub Actions fallback; schedules DISABLED, manual dispatch only
run_vm.sh             # VM runner: loads .env, runs run.py --mode daily --skip ingest,write
AGENT_GRAPH.md        # original design doc — background only, see the note at the top
```

## Setup

1. Python 3.12 venv (workflows use 3.11; either works): `python3.12 -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt`. Install torch separately from the CPU-only index (see `.github/workflows/daily.yml`); a `--index-url` line is not valid inside `requirements.txt`.
2. `ffmpeg` on PATH.
3. Kokoro TTS + faster-whisper models are cached under `~/.cache/huggingface/hub/`. For offline model use: clear proxy env vars and set `HF_HUB_OFFLINE=1` (see `run_vm.sh` — the runtime injects bracketed IPv6 `no_proxy` values that break httpx parsing).
4. Copy `.env.example` to `.env` (0600, never committed) and fill in the values: `PIXABAY_API_KEY=...` (illustrative b-roll only), `TELEGRAM_BOT_TOKEN=...`, `TELEGRAM_CHAT_ID=...`. `GEMINI_API_KEY` is also referenced by the workflows and the paused daily write stage; it is not needed for the scout loop.
5. `yt-dlp` at `~/workspace/tools/bin/yt-dlp` for TikTok / X direct media. It has no Threads extractor.
6. Run the mechanical stages (daily mode is paused — manual / resumed runs only): `./run_vm.sh daily`.

## Run a scout run (manual)

Follow `scout/README.md` and the job body in `crons/` — the summary in "The operator loop" above is not a substitute. Notes that matter:

- X has no connector and no saved login. Use public methods only: public post pages, fxtwitter API via curl, web search, microlink screenshots. X timelines are often unreadable (Cloudflare, 404, profile-only 200, HTML instead of JSON) — report unreadable accounts with the next published clip, never guess at them. When fxtwitter returns 404 for a post, the vxtwitter API works, and direct twimg mp4 URLs download cleanly. Never start a login flow on your own and never push the user for an X login.
- Threads is connected via `threads-cli` on the user's linked account. Resolve each listed account every run from the linked account's following list — never hardcode numeric user IDs, never scrape threads.com. Page `profile-threads` at most 3 pages per run, stop at the first post already in `scout/saved_items.json`. A 429 ends ALL Threads calls for that run — stop, do not retry. Re-page each profile at the END of the run: Threads listings lag new posts ~30 minutes. Record seen permalinks in `scout/state.json` `seen_threads_urls`.
- A Threads post mirroring an already-saved X post (same author, same story, same day, near-identical text) is coverage, not a new find: save it noting the X post_id it mirrors, and NEVER pick it on its own. Only Threads posts with no X counterpart are eligible picks.
- Threads keyword search runs the same combined queries as X, via `threads-cli search` (Top tab; `--recent 1` only if Top returns nothing notable; max 1 page per call). Save hits as `threads:keyword:<query>` with the Threads permalink.

## Build a narrated clip from a find

One folder per clip: `pipeline/output/scout/clips/<date>_<slug>/`. The per-clip pattern (see any recent folder, e.g. `20261105_kimi_k3_in_c` or `20261105_gpt6_cyber_launch`):

1. `script.json` — title, `sentences` (the narration, verified text only — no invented facts, dates, or quotes), `bio_lines` (one element: the Source line, see below), shot list.
2. `tts_driver.py` — synthesizes the narration sentence by sentence via `pipeline/tts.py` (`seg_wav`), assembles `narration.wav` (segments + 0.2s gaps), writes `words.json` / `sentences.json` (word timings from Kokoro's own tokens).
3. `render.py` — generates `frame_*.png` via `pipeline/clip_frames.py` (dynamic hug) and `captions.ass` (terminal typewriter, top-anchored).
4. `assemble.py` — slices `narration.wav` at the shot boundaries, builds each shot segment, concats, loudnorms the full narration (two-pass, I=−14/−15, TP=−1.5, LRA=11; see the clip's assemble.py for its exact target), burns `captions.ass`, faststart. ffmpeg `alimiter` takes a LINEAR limit (0.0625–1), not dB — `limit=-1dB` mis-parses and RAISES peaks. Never use it.
5. `finalize.py` — writes `description.txt` + `meta.json`, checks the Flesch-Kincaid gate (≤ 9.5) and the watermark geometry, records the file md5/size. QA before publishing: ffprobe clean, no black segments, frames eye-verified at start/middle/end, captions top-anchored with zero caption-green above y1500, watermark beneath the bio.

Source-video clips (the source has usable audio/video) follow the same folder pattern but keep the source audio and use the source footage as the backbone — see `templates/clips/template.yaml` `footage_priority_2026_10_27`. A narrated clip can also use moving video shots, not just stills: per-shot transparent RGBA overlays (title + bio + watermark, dynamic-hug geometry) composited over trimmed video segments — see `20261105_swarm_site` (`build_overlays.py` + `assemble.py`).

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
- **Footage priority**: (1) source/company explaining on video, with its own audio, as the backbone; (2) other useful footage as cutaways; (3) vision-cropped root-source stills only when no video exists; (4) narration last. NEVER a third-party surfacing post as a visual — a surfacing-post visual FAILS QA. No pure-text shots (numbers ride real visuals only — charts, banners, tickers, callouts — or the figure is dropped). Eye-verify every segment; video must move; source audio first; hard cuts only.
- **Footage hunt** (mandatory for Threads-sourced picks): run `pipeline/threads_media.py` on the surfacing post BEFORE any stills fallback and log the attempt + result in `meta.json`. Also sweep the surfacing account's other same-story posts from the last 24h, and when the root source is an article/blog page, list EVERY visual on the page before choosing shots. The script fetches through curl, not Python urllib, and keeps the bare `Mozilla/5.0` user agent — "improving" either gets a reduced page with no media URLs. Video posts yield only a poster from that route; Threads video needs the browser embed-page download. TikTok / X direct media: `yt-dlp`.
- **No mid-screen text without an analytical chart.** Visuals change exactly when the narration's subject changes; an evidence shot never shows its subject before the subject is named.
- **QA bar**: no black frames, no file that fails ffprobe, no verification walls or popups, headlines fully in frame. A render only counts as done once it is in the Telegram review queue.

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

- X timelines are often unreadable from public methods (see "Run a scout run"). Threads is the reliable source right now; every recent pick came via Threads.
- Threads profile listings lag new posts ~30 minutes — re-page at the end of every run.
- The Threads connector returns text only, never media — a hunt that stops at the connector has not hunted at all.
- `pipeline/threads_media.py` must use curl with a bare `Mozilla/5.0` UA (see above). On multi-image carousels it extracts only the first image.
- Microlink screenshots (`pipeline/visuals.py`) are mobile-viewport (500x900); Reuters bot-walls them. Chromium CLI screenshots produce nothing in this environment — use microlink or the browser.
- The VM is memory-constrained (~500MB real headroom, no swap); renders are single-flight. `run.py` hands off to `render.py` as a separate process — killing the wrapper does not stop the render; kill `render.py` itself plus orphaned ffmpeg children, then verify `ps` is clean.
- `/tmp` is small and cleaned between turns — keep anything needed under `~/workspace/`, and keep source media inside the clip folder.
- `AGENT_GRAPH.md` is stale background (see the note at the top). The daily-digest rules in the old root README (cold open, person photos as hook heroes, 1.10x voice) are superseded — this file replaces that README as the handover.
