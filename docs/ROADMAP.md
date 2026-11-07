# AI News Video Pipeline — Master Technical Roadmap

> **Pipeline Version:** `2026.11.06.13`  
> **Brand & Distribution:** `@leos.logos`  
> **Repository:** `github.com/leogacc/ai-news-video-pipeline`  
> **Author:** Antigravity (Pair Programming with User / Creative Director)  
> **Status:** Active Engineering 🚀 (Phases 1–8 Complete ✅; TikTok 200-View Jail Breakout & Terminal Polish Deployed)  

---

## 1. Executive Summary & Strategic Pivot

Based on the operational review and direct directive from the Creative Director on 2026-11-05, this roadmap outlines the evolutionary transition of the **AI News Video Pipeline**. 

### The Core Shifts
1. **Environment Bootstrapping:** Transition the current remote VM from a passive inspection/code-maintenance checkout into a fully operational, self-contained production runner with automated virtual environment setup, model caching, and secret management.
2. **Decommissioning Threads & Transitioning to Free X Search:** Cease reliance on the Threads connector and `threads-cli`. Replace it with a robust, cost-free, automated mechanism to search and ingest high-signal AI news from X.
3. **Cloud Crons Orchestration:** Transition automated scheduled runs (07:00, 11:00, 16:00, 19:00 PT) to cloud-managed crons driven by Antigravity.
4. **Remotion Animation Engine:** Integrate Remotion (React/TypeScript) to produce dynamic, entertaining, and educational visual animations for high-impact research papers and abstract finds that lack native source video.
5. **Codification of the "TikTok Worthiness Scorecard":** Formalize the Excitement Gate with quantitative and qualitative criteria ensuring every candidate find is entertaining, informative, and engaging for vertical short-form audiences.
6. **Preservation of Paused Subsystems:** Keep high-volume multi-story digests and 16:9 long-form formats securely cataloged in the backlog for future reactivation.

---

## 2. Phase 1: Environment Bootstrapping & Technical Spikes (Immediate)

```mermaid
flowchart LR
    subgraph P1 ["Phase 1: Bootstrapping & Technical Spikes"]
        SETUP["1.1 setup_env.sh\n(Venv, Torch CPU, Kokoro Cache, .env)"]
        SPIKE_X["1.2 Free X Search Spike\n(Dorks + fxtwitter vs Scrapers vs RSS)"]
        SPIKE_CRON["1.3 Cloud Crons Spike\n(GitHub Actions vs Cloud VM vs Goal Cron)"]
    end
    SETUP --> P1_EXIT{"Phase 1 Exit Gate"}
    SPIKE_X --> P1_EXIT
    SPIKE_CRON --> P1_EXIT
```

### Objective 1.1: Automated VM Environment Bootstrapper (`setup_env.sh`)
* **Goal:** Create an idempotent shell script (`setup_env.sh`) that bootstraps the VM from zero to full production capability.
* **Implementation Details:**
  1. Provision a Python 3.12 virtual environment at `.venv/`.
  2. Install PyTorch CPU-only (`--index-url https://download.pytorch.org/whl/cpu`).
  3. Install core dependencies from `pipeline/requirements.txt`.
  4. Install VM-specific pinned packages from `pipeline/requirements-vm.txt` (specifically locking `av==16.1.0` to avoid faster-whisper crash, `opencv-python-headless`, and `Pillow`).
  5. Pre-warm and cache Kokoro-82M weights and tokenizer to `~/.kokoro_cache` / HuggingFace hub cache with `HF_HUB_OFFLINE=1` readiness.
  6. Generate a local `.env` template configured with permissions `0600` containing placeholders for `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `PIXABAY_API_KEY`.
* **Deliverable:** Working `setup_env.sh` and verified `.venv` environment.
* **Status:** **Complete (2026-11-06)** — `setup_env.sh` created and executed; CPU PyTorch, pinned `av==16.1.0`, `kokoro` weights cached, `.env` secured (0600), live Telegram ping verified, and all TTS tests passing.

### Objective 1.2: Free X Search Investigation Spike
* **Goal:** Benchmark and identify the most reliable, zero-cost method for searching X public posts without requiring user logins or risking anti-bot blockades.
* **Candidates under Evaluation:**
  * **Candidate A (Search Engine Dorks + API Resolution):** Query Google / DuckDuckGo via lightweight curl or SerpAPI free tiers with targeted dorks (`site:x.com (AI OR LLM OR "new model") min_faves:500`), then fetch full metadata via `api.fxtwitter.com` or `api.vxtwitter.com`.
  * **Candidate B (Unofficial Scrapers):** Python libraries utilizing guest tokens or mobile endpoint reverse engineering (e.g., `twikit`, `ntscraper`).
  * **Candidate C (Public Syndication & Nitter Mirrors):** Querying reliable Nitter RSS endpoints or public Twitter syndication widgets (`cdn.syndication.twimg.com`).
* **Evaluation Criteria:**
  * Resilience against IP rate limits and Cloudflare challenge walls.
  * Fidelity of media URL extraction (direct mp4/jpg vs poster stills).
  * Latency and execution footprint within the VM sandbox.
* **Deliverable:** Spike report with recommended implementation architecture.
* **Status:** **Complete (2026-11-06)** — Benchmark suite `scout/spike_x_search.py` executed across 14 VIP accounts (100% success, 0.40s latency, ~1,100 posts ingested) and Google News RSS (`site:x.com`, 100 hits/query). Report delivered in `docs/spikes/FREE_X_SEARCH_SPIKE.md`. Official dark-mode X post screenshot feature added and verified in `pipeline/tweet_card.py` with full unit test suite `pipeline/test_tweet_card.py` (100% pass).

### Objective 1.3: Cloud Crons Platform Evaluation Spike
* **Goal:** Determine the optimal execution architecture for the 4x-daily finds scout schedule (07:00, 11:00, 16:00, 19:00 PT).
* **Candidates under Evaluation:**
  * **Option A (GitHub Actions Scheduled Matrix):** Utilize `.github/workflows/daily.yml` updated with cron schedules and repository secrets.
  * **Option B (Antigravity Cloud Crons / Goal Tasks):** Utilize the platform's native task scheduler running against markdown definitions in `crons/`.
  * **Option C (Dedicated Headless Cloud Runner):** Continuous lightweight daemon/systemd timer invoking `run_vm.sh`.
* **Evaluation Matrix:** Cold-start latency, secret isolation, network proxy compatibility, and execution consistency.
* **Deliverable:** Architectural selection report for scheduled execution.
* **Status:** **Complete (2026-11-06)** — Benchmarked in `scout/spike_cloud_crons.py` (3.68s warm-start vs ~270s GHA, sub-millisecond atomic state writes, 0600 secret isolation, cached Kokoro-82M & YuNet models). Spike report delivered in `docs/spikes/CLOUD_CRONS_SPIKE.md`. Option B (Antigravity Cloud Crons) selected. All four daily cron jobs in `crons/` modernized to purge Threads, wire Free X Search, and codify the TikTok Excitement Gate.

### Phase 1 Exit Criteria — ALL COMPLETE ✅
- [x] `setup_env.sh` executes cleanly, producing a functional `.venv` and verified Kokoro TTS offline synthesis (Phase 1.1).
- [x] Winner of the Free X Search spike selected with code proof-of-concept and official X post screenshot feature verified (Phase 1.2).
- [x] Cloud Crons platform selected with validated execution pathway and modernized cron specifications (Phase 1.3).

---

## 3. Phase 2: Ingestion & Animation Skill Implementation

```mermaid
flowchart LR
    subgraph P2 ["Phase 2: Ingestion & Animation"]
        X_ENG["2.1 Free X Search Engine\n(Retire Threads, Deploy x_search.py)"]
        REMOTION["2.2 Remotion Animation Engine\n(React/TS, Node 24, Paper Graphics)"]
        INTEG["2.3 Assembly Integration\n(Dynamic Hug + Remotion MP4 Overlays)"]
    end
    X_ENG --> P2_EXIT{"Phase 2 Exit Gate"}
    REMOTION --> INTEG --> P2_EXIT
```

### Objective 2.1: Production Free X Search Engine
* **Goal:** Build and deploy `pipeline/x_search.py`, fully replacing the Threads scouting logic.
* **Tasks:**
  1. Retire `scout/threads.yaml` and archive `pipeline/threads_media.py`.
  2. Implement `pipeline/x_search.py` implementing the winning spike approach with automated fallbacks.
  3. Ensure clean deduplication against `scout/saved_items.json` and `scout/state.json`.
  4. Ensure media extraction downloads high-resolution twimg images and raw MP4 video streams without third-party watermarks.
* **Status:** **Complete (2026-11-06)** — `pipeline/x_search.py` implemented with VIP timeline monitoring (Syndication API), keyword discovery (Google News RSS), single-tweet hydration, and direct 1080p MP4 downloading (`video.twimg.com`). `scout/x_scout.py` implemented as the production cron orchestrator with the TikTok Excitement Gate and atomic persistence. Threads archived to `archive/threads/`. Full unit test suite `pipeline/test_x_search.py` passing (6/6).

### Objective 2.2: Remotion Animation Engine for Abstract Finds & Papers
* **Goal:** Implement an automated motion-graphics renderer using Remotion (React/TypeScript) on Node.js 24 to turn abstract papers, benchmarks, and non-visual finds into engaging video cutaways.
* **Tasks:**
  1. Leverage foundational templates in `skills/local_animated_data_visualization/`.
  2. Implement parameterized Remotion compositions for:
     * **Benchmark Comparative Ladders:** Dynamic bar-chart comparisons illustrating performance jumps over baseline models.
     * **Architecture Flow Diagrams:** Visualizing multi-agent workflows, model pipelines, or security exploit chains.
     * **Kinetic Metric Counters:** Rapid-counter displays highlighting quantitative achievements (e.g., parameter counts, latency reductions, exploit counts).
  3. Comply strictly with channel art direction:
     * Pure black background (`#000000`).
     * Neon green accents (`#39FF14`) and clean white typography.
     * 1080x1920 portrait canvas formatted to H.264 High L4.0, 30fps.
  4. Build automated CLI bridge: `pipeline/animations/render.mjs` and Python wrapper `pipeline/animations.py`.
* **Status:** **Complete (2026-11-06)** — `pipeline/animations/` package built with React 19/TypeScript and Remotion. Implemented `BenchmarkLadder`, `ArchitectureDiagram`, and `KineticMetricCounter` with tabular figures, spring physics, and neon green glowing accents. Automated CLI renderer `pipeline/animations/render.mjs` and Python bridge `pipeline/animations.py` deployed and verified. Full test suite `pipeline/test_animations.py` passing (6/6).

### Objective 2.3: Video Assembly Integration
* **Goal:** Seamlessly integrate Remotion-rendered cutaways into `pipeline/clip_frames.py` and `assemble.py`.
* **Tasks:**
  1. Allow clips to seamlessly alternate between moving source video, Remotion motion graphics, and vision-cropped stills.
  2. Maintain the Dynamic Hug geometry (Title above, single-line regular Bio below, `@leos.logos` watermark at alpha 51).
* **Status:** **Complete (2026-11-06)** — Extended `pipeline/clip_frames.py` with `build_video_overlay` and Dynamic Hug filtergraph logic. Deployed `pipeline/assemble.py` supporting multi-shot declarative clip builds, Kokoro TTS audio synchronization, top-anchored terminal typewriter captions (`pipeline/captions.py`), and -14 LUFS loudnorm. Full unit test suite `pipeline/test_assemble.py` passing.

### Phase 2 Exit Criteria
- [x] Free X Search routinely discovers new AI finds without authentication errors or rate-limit lockouts.
- [x] A sample research paper find is successfully synthesized into a 30s video featuring a custom Remotion animated benchmark chart (`pipeline/output/scout/clips/sample_paper_find/clip.mp4`).

---

## 4. Phase 3: Editorial Scoring & Cloud Cron Orchestration

```mermaid
flowchart LR
    subgraph P3 ["Phase 3: Editorial & Scheduling"]
        SCORE["3.1 TikTok Worthiness Scorecard\n(Hook, Ed, Entertainment, Stakes)"]
        RULES["3.2 Update Scout Rules & Template\n(scout/README.md & template.yaml)"]
        CRON_DEP["3.3 Cloud Crons Deployment\n(Active 4x-Daily Schedules)"]
    end
    SCORE --> RULES --> P3_EXIT{"Phase 3 Exit Gate"}
    CRON_DEP --> P3_EXIT
```

### Objective 3.1: Codified "TikTok Worthiness Scorecard"
* **Goal:** Update the Excitement Gate with a concrete evaluation rubric to ensure every candidate find is worthy of a vertical short-form video.
* **The 4-Pillar Scorecard (Minimum Passing Score: 28 / 40, no pillar < 6):**
  1. **Hook Strength (0–10):** Can the core idea be expressed in a single visceral statement under 3 seconds? (e.g., *"72 AI agents built a website as visible mouse cursors"* = 10; *"Version 1.4 adds SQLite support"* = 2).
  2. **Educational & Explanatory Value (0–10):** Does the viewer walk away understanding a real mechanism, capability, or paradigm shift?
  3. **Visual Entertainment Potential (0–10):** Can the story be driven by captivating moving footage or a custom Remotion graphic, avoiding static walls of text?
  4. **Relatable Stakes (0–10):** Does this matter to the average interested person rather than just niche library maintainers?
* **Updates:** Document the scorecard and reference case studies in `scout/README.md` and `templates/clips/template.yaml`.
* **Status:** **Complete (2026-11-06)** — Codified 4-Pillar Scorecard and Tier 1 explicit disqualifiers implemented in `scout/x_scout.py:excitement_gate_score()`. Full rubric, scoring weights, and reference positive/negative case studies documented in `scout/README.md`. Editorial curation rule `tiktok_worthiness_scorecard_2026_11_06` synced to `templates/clips/template.yaml`. 10/10 dedicated unit tests passing in `scout/test_scorecard.py`, and 31/31 regression tests passing across all test suites.

### Objective 3.2: Cloud Crons Deployment
* **Goal:** Deploy and verify the 4 daily scout runs via the selected cloud cron mechanism.
* **Schedule (Pacific Time):**
  * `07:00 PT`: Morning Scout Pass
  * `11:00 PT`: Midday Scout Pass
  * `16:00 PT`: Afternoon Scout Pass
  * `19:00 PT`: Evening Scout Pass
* **Execution Contract:**
  * Runs check deduplication first.
  * Applies the TikTok Worthiness Scorecard.
  * If a pick passes the bar, builds the clip and pushes MP4 + TikTok description to Telegram.
  * If no pick passes the bar, updates `scout/saved_items.json` and exits silently.
* **Status:** **Complete (2026-11-06)** — Deployed automated non-interactive runner mode `scout/x_scout.py --run-cron` integrating candidate ingestion, scorecard evaluation, declarative clip assembly via `pipeline/assemble.py`, Remotion cutaways, and Telegram review queue delivery. All 4 scheduled tasks in `crons/` (`07:00`, `11:00`, `16:00`, `19:00` PT) updated to active status and wired to `.venv/bin/python3 scout/x_scout.py --run-cron`. Unit test suite `scout/test_cron_runner.py` created (5/5 passing) and full regression suite passes 36/36 tests.

### Phase 3 Exit Criteria — ALL COMPLETE ✅
- [x] Updated `scout/README.md` and `templates/clips/template.yaml` committed with Codified TikTok Worthiness Scorecard.
- [x] Cloud Crons live and successfully trigger at scheduled times with automated execution contract verified.

---

## 5. Phase 4: End-to-End Validation & Production Cutover
* **Status:** **Complete (2026-11-06)** — All Phase 4 objectives and deliverables verified and locked.

```mermaid
flowchart TD
    E2E["4.1 Dry-Run Automated Cycle\n(Ingest X -> Score -> Render Remotion/Clip -> QA)"]
    TG_CHECK["4.2 Telegram Review Queue Verification\n(Delivery of MP4 + Description)"]
    PROD_LOCK["4.3 Version Bump & Production Lock\n(v2026.11.06.8 in VERSION & CHANGELOG)"]

    E2E --> TG_CHECK --> PROD_LOCK
```

### Objective 4.1: End-to-End Dry-Run & Quality Assurance
* **Goal:** Execute a full autonomous run from discovery to Telegram delivery without manual intervention.
* **Verification Checklist:**
  * [x] Video matches delivery specs (1080x1920, H.264 High L4.0, yuv420p, faststart, `-14` LUFS).
  * [x] Captions top-anchored at `~y1513` in terminal neon green (`#39FF14`).
  * [x] Bio box holds single regular-weight Source line (`Source: <root>, <date>`).
  * [x] Watermark `@leos.logos` present under bio at 20% opacity.
  * [x] Automated QA (`pipeline/qa.py --clip`, `pipeline/pin_edge_check.py`) passes without blocking exceptions.
  * [x] Telegram receives both the high-res MP4 and the copy-paste-ready description.
* **Status:** **Complete (2026-11-06)** — Automated Clip QA Gate codified in `pipeline/qa.py --clip` with 5 dedicated unit tests in `pipeline/test_qa_clip.py`. Re-assembled sample clip and live dry-run passed all checks. Live Telegram dispatch verified via `@aividpipBOT` (`chat_id: 1904835992`).

### Objective 4.2: Production Version Bump & Documentation Handover
* **Goal:** Finalize versioning per `skills/local-pipeline-upgrade/SKILL.md`.
* **Tasks:**
  * [x] Bump `pipeline/VERSION` to `2026.11.06.8`.
  * [x] Document all changes in `pipeline/CHANGELOG.md`.
  * [x] Update root `README.md` reflecting the new operational workflow.
* **Status:** **Complete (2026-11-06)** — `pipeline/VERSION` bumped to `2026.11.06.8`. `pipeline/CHANGELOG.md` updated with full release notes. Root `README.md` updated to reflect the new Free X Search, Remotion graphics, declarative assembler, 4-pillar scorecard, and automated crons.

---

## 6. Phase 5: TikTok Safe-Zone Rectification & Quick Wins (Immediate / Next Up)

```mermaid
flowchart LR
    subgraph P5 ["Phase 5: Safe-Zone & Quick Wins (Immediate)"]
        CAP_SAFE["5.1 Captions Relocation\n(MarginV=1513 -> y=1100 Center)"]
        QA_SAFE["5.2 QA Safe-Zone Gate\n(Update qa.py for y=850..1350)"]
        AUDIO_BED["5.3 Ducked Music Bed\n(sidechaincompress: -22dB / -16dB)"]
        HOOKS["5.4 Viral Hook Engineering\n(Curiosity Gap & Loss Aversion)"]
    end
    CAP_SAFE --> QA_SAFE --> P5_EXIT{"Phase 5 Exit Gate"}
    AUDIO_BED --> P5_EXIT
    HOOKS --> P5_EXIT
```

### Objective 5.1: Subtitle UI Safe-Zone Relocation
* **Problem Statement:** In `pipeline/captions.py:179` and `pipeline/assemble.py:110`, captions use `MarginV=1513, Alignment=7` (top-left alignment with top margin 1513px). This forces subtitle baseline into $y = 1513 \dots 1750$ px. On TikTok's native 1080x1920 mobile interface, the bottom UI overlay (creator handle `@leos.logos`, multi-line description, hashtags, sound pill ticker, and scrubber bar) occupies $y = 1450 \dots 1920$ px. Subtitles render directly underneath TikTok UI text, causing cognitive friction and instant swipe-aways ($<35\%$ 3-second retention).
* **Technical Specification:**
  1. Elevate subtitle anchor in `pipeline/captions.py` and `pipeline/assemble.py` from `MarginV: 1513` to `MarginV: 1100` (or `Alignment: 5` middle-center at $y \approx 1100$).
  2. Confine caption rendering to the **Golden Subtitle Zone** ($y = 1050 \dots 1250$ px), perfectly clear of both top search/navigation tabs ($y \le 220$ px) and bottom platform overlays ($y \ge 1450$ px).
  3. Keep maximum caption line length to $\le 6$ words per chunk to prevent collisions with the right-side engagement column ($x \ge 920$ px).
* **Deliverable:** Updated `pipeline/captions.py` and `pipeline/assemble.py` generating mobile-safe ASS subtitles.
* **Target Metric:** 3-second hold rate increases from $\approx 35\%$ to $\ge 55\%$.
* **Status:** **Complete (2026-11-06)** — Elevated top-anchored subtitle margin in `captions.py` and `assemble.py` to `MarginV=1180` ($y \approx 1150 \dots 1280$) backed with an ASS `BorderStyle=3` dark translucent pill box (`&H40000000`, 14px padding) over the lower portion of central cards. 100% clear of the TikTok bottom UI overlay ($y \ge 1450$).

### Objective 5.2: Automated QA Safe-Zone Assertion Modernization
* **Problem Statement:** In `pipeline/qa.py:170-176`, the automated QA suite strictly checks:
  ```python
  margin_v = int(parts[21])
  if margin_v >= 1400:
      has_top_anchor = True
  clip_check("captions top-anchored safe area", has_top_anchor, "(MarginV >= 1400)")
  ```
  This assertion artificially blocks moving subtitles into the actual visible safe area.
* **Technical Specification:**
  1. Update `pipeline/qa.py` to validate that captions sit inside the verified platform safe vertical band:
     ```python
     is_in_safe_zone = (1050 <= margin_v <= 1350)
     clip_check("captions safe-zone vertical alignment", is_in_safe_zone)
     ```
  2. Update `pipeline/test_qa_clip.py` to assert the new safe-zone boundaries and `BorderStyle=3` box backdrop across all test fixtures.
* **Deliverable:** Modernized `pipeline/qa.py` and passing test suite in `pipeline/test_qa_clip.py`.
* **Status:** **Complete (2026-11-06)** — Updated `pipeline/qa.py` to enforce `1050 <= MarginV <= 1350` and `BorderStyle=3`. `pipeline/test_qa_clip.py` updated with passing safe-zone and failing overlay tests (6/6 passing).

### Objective 5.3: Automated Sidechain-Ducked Music Bed
* **Problem Statement:** Background music is currently disabled (`pipeline/assets/music/ai_digest_bed.mp3.disabled`). In `pipeline/assemble.py:481-482`, only speech narration (`1:a`) is multiplexed into the output. On TikTok—a sound-first platform—a dead-silent background behind synthetic narration triggers algorithmic penalties and viewer drop-off.
* **Technical Specification:**
  1. Introduce royalty-free / CC0 tech-pulse ambient beds in `pipeline/assets/music/` (e.g. `tech_pulse_bed.mp3`).
  2. Update `pipeline/assemble.py` to multiplex audio via FFmpeg `sidechaincompress`:
     * Narration voiceover normalized to **-14 LUFS** (ITU-R BS.1770-4).
     * Background music ducked to **-22 dB LUFS** during speech.
     * Background music smoothly ramping to **-16 dB LUFS** during natural pauses ($>0.25$s).
     * Unified mix passed through `loudnorm=I=-14:LRA=11:TP=-1.0`.
* **Deliverable:** Multi-track dynamic audio ducking in `pipeline/assemble.py`.
* **Status:** **Complete (2026-11-06)** — Re-enabled `ai_digest_bed.mp3`. Wired multi-stream sidechain ducking filtergraph into `pipeline/assemble.py` with `asplit=2`, `threshold=0.03`, `ratio=8`, `attack=20`, `release=350`, `volume=-16dB`, and `loudnorm=I=-14:LRA=11:TP=-1.0`. Passes QA loudness gate (-14.4 LUFS).

### Objective 5.4: High-Retention Editorial Hook Engineering
* **Problem Statement:** Ingested stories currently open with wire-service press release phrasing (*"Google on Wednesday unveiled Gemini 4 Carbon..."* or *"DeepSeek announced..."*), which causes viewer abandonment within the first 1.5 seconds.
* **Technical Specification:**
  1. Update `scout/x_scout.py:format_tiktok_description()` and clip narration generation to mandate 4 proven psychological hook frameworks:
     * **Curiosity Gap:** *"Google just leaked their biggest AI release of the year, and they swore this was impossible."*
     * **Negative Framing / Loss Aversion:** *"Stop coding with Claude 3.5 until you turn off this one dangerous setting."*
     * **High Stakes / David vs Goliath:** *"This brand-new open-source AI just made $200k OpenAI subscriptions completely obsolete."*
     * **Open Loop:** Ending the video with a phrase that grammatically completes the opening sentence for an infinite seamless replay.
  2. Enforce Whisper ASR SEO: mandate that the primary entity keyword (e.g. *"DeepSeek-R1"*, *"ChatGPT Search"*) is spoken aloud within the first **2.5 seconds** for TikTok search indexing.
* **Deliverable:** Updated script generation rules in `scout/x_scout.py`.
* **Status:** **Complete (2026-11-06)** — Implemented `generate_hook_and_script()` in `scout/x_scout.py` with dynamic 3-archetype selector (Benchmark Clash, Direct Stakes, Disruption) and engagement debate questions. Enforces vocalization of primary entity in $< 2.5$ seconds (< 5 words). Fully integrated into `format_tiktok_description` and `build_clip_for_pick`.

### Phase 5 Exit Criteria — ALL COMPLETE ✅
- [x] Subtitles rendered at $y \approx 1180$ px with 0 pixels entering the TikTok bottom dead zone ($y \ge 1450$ px) or right column ($x \ge 920$ px).
- [x] `pipeline/qa.py` asserts mobile safe zone boundaries and 48/48 unit tests pass.
- [x] Automated FFmpeg multi-track sidechain ducking active with music ducked to -22 dB during speech.
- [x] Hook generation in `scout/x_scout.py` produces Benchmark Clash / Loss Aversion / Disruption hooks with vocalized keywords in seconds 0–2.5.
- [x] Live dispatch of updated sample clip verified in Telegram `@aividpipBOT` review queue.

---

## 7. Phase 6: Broadcast Studio Voice & High-Velocity Pacing ($0 Budget)

```mermaid
flowchart LR
    subgraph P6 ["Phase 6: $0 Studio Voice & Pacing"]
        GOOGLE_TTS["6.1 Google Cloud TTS\n(Studio-O / Journey Voices)"]
        QUOTA_SAFE["6.2 3-Layer Zero-Spend Gate\n(800k Local Ceiling + Kokoro Fallback)"]
        KINETIC_CAPS["6.3 Word-by-Word Bouncing Caps\n(Electric Yellow Popups at y=1100)"]
        PACING["6.4 High-Velocity Pacing\n(2.0s ASL + Ken Burns Zooms)"]
    end
    GOOGLE_TTS --> QUOTA_SAFE --> P6_EXIT{"Phase 6 Exit Gate"}
    KINETIC_CAPS --> P6_EXIT
    PACING --> P6_EXIT
```

### Objective 6.1: Zero-Cost Google Cloud TTS Studio Voice Integration
* **Budget Constraint Proof:** Strictly **$0.00 incremental budget**.
  * User holds a **$20/month Google AI Pro plan** (Google One AI Premium).
  * Google Cloud Text-to-Speech provides a permanent, recurring free tier of **1,000,000 characters per month** for Studio (`en-US-Studio-O`) and Journey (`en-US-Journey-D`) voices, plus 4,000,000 characters for WaveNet/Standard.
  * Google AI Pro users receive **$10.00/month in recurring Google Cloud credits** via Developer Program benefits.
  * Production volume: 4 videos/day $\times$ 30 days = 120 videos/month $\times$ 1,700 chars/script = **~204,000 chars/month** (only **20.4%** of the 1M free allowance).
* **Technical Specification:**
  1. Build `pipeline/google_tts.py` utilizing `google-cloud-texttospeech_v1beta1`.
  2. Implement voice selection: `en-US-Studio-O` (Broadcast studio male) or `en-US-Studio-Q` (Authoritative female) at `speaking_rate: 1.18`.
  3. Extract exact word timestamps using SSML `<mark name="w{i}"/>` timepointing (`TimepointType.SSML_MARK`). Populate `words.json` seamlessly without running offline Whisper passes.

### Objective 6.2: 3-Layer Zero-Spend Defense Architecture
* **Goal:** Guarantee zero accidental billing under all operational conditions.
* **Architecture:**
  * **Layer 1 (Local Quota Tracker):** `pipeline/google_tts.py` logs monthly character usage to `pipeline/.gcp_tts_quota.json`. Enforces a strict local ceiling of **800,000 characters/month** (80% of free tier). If characters $\ge 800\text{k}$, immediately switches synthesis to local Kokoro TTS.
  * **Layer 2 (Cloud Billing Alerts):** Configurable $1.00 GCP budget alert with automated API kill-switch.
  * **Layer 3 (Resilient Fallback):** If network offline, API credential absent, or HTTP 429/500 encountered, automatically falls back to local offline Kokoro TTS (`am_echo` @ 1.20x) without failing the pipeline.

### Objective 6.3: Kinetic Word-by-Word Bouncing Highlight Subtitles
* **Problem Statement:** Letter-by-letter monospace typewriter captions (`DejaVu Sans Mono`, `#39FF14`) create visual reading fatigue at 1.20x TTS speed (~200 WPM) and feel like an outdated terminal screen rather than engaging video.
* **Technical Specification:**
  1. Transition from letter typewriter to **dynamic word-by-word active highlight captions**.
  2. Display 2–4 words on screen at a time, centered at $y \approx 1100$ px.
  3. Highlight active spoken word in **Electric Cyber Yellow (`#FFE600`)** with a $1.15\times$ kinetic spring scale bounce on word onset.
  4. Use modern high-impact typography: `Montserrat ExtraBold` or `Inter Black` with black drop shadow (`&HFF000000`) for universal legibility across all backgrounds.

### Objective 6.4: High-Velocity Visual Cadence (1.6s–2.2s ASL)
* **Problem Statement:** Average Shot Length (ASL) is currently 7.50 seconds per shot, causing viewers to stare at static graphics for 6+ seconds after initial animation completes.
* **Technical Specification:**
  1. Reduce maximum shot duration in `pipeline/assemble.py` and `scout/x_scout.py` to **1.6s – 2.2s**.
  2. Cut 30-second clips into 14–18 visual micro-beats (e.g. wide chart $\to$ zoom cut to winner bar $\to$ cut to tweet card $\to$ zoom to author badge $\to$ cut to code terminal).
  3. Implement automated **Ken Burns continuous push-in** ($100\% \to 108\%$ slow digital zoom) on still cards and screenshots via FFmpeg `zoompan` or Remotion transforms, ensuring 0 seconds of motionless video.

### Phase 6 Exit Criteria — ALL COMPLETE ✅
- [x] `pipeline/google_tts.py` successfully synthesizes broadcast audio via `en-US-Studio-O` at 1.18x with SSML word timepoints matching `words.json`.
- [x] 3-layer zero-spend safety architecture verified: quota saturation test cleanly switches to local Kokoro TTS with $0 out-of-pocket spend (`.gcp_tts_quota.json`).
- [x] Kinetic word-by-word bouncing captions active in the center-safe area (`MarginV=1180`, Electric Cyber Yellow active word highlight).
- [x] Video assembly achieves high-velocity pacing with continuous subtle Ken Burns digital micro-zooms on still assets.
- [x] Flagship sample clip re-assembled, passed Automated Clip QA Gate, and verified with 53+ passing unit tests.

---

## 8. Phase 7: Production Polishing, Spring Dynamics & Remotion Modernization

```mermaid
flowchart LR
    subgraph P7 ["Phase 7: Production Polish & Remotion"]
        SPRINGS["7.1 Remotion Springs\n(damping:12, mass:0.5, stiffness:110)"]
        THEME["7.2 Modern Dark Theme\n(Inter/Montserrat, Glassmorphism #0B0F19)"]
        CARD_3D["7.3 3D Tilt TweetCard\n(Perspective rotateX + SVG highlighter)"]
        SFX_ENG["7.4 Transition SFX\n(Whooshes, UI pops, Bass drop)"]
        CACHE["7.5 Webpack Bundle Cache\n(Save 25-35s render latency)"]
    end
    SPRINGS --> THEME --> P7_EXIT{"Phase 7 Exit Gate"}
    CARD_3D --> P7_EXIT
    SFX_ENG --> P7_EXIT
    CACHE --> P7_EXIT
```

### Objective 7.1: Remotion Physics-Based Spring Dynamics
* **Problem Statement:** `pipeline/animations/src/theme.ts` uses mathematical cubic polynomials (`easeOutCubic`, `easeOutExpo`) that clamp animations abruptly without natural physical momentum.
* **Technical Specification:**
  1. Replace polynomial easing across all Remotion compositions (`BenchmarkLadder`, `ArchitectureDiagram`, `KineticMetricCounter`) with Remotion’s mass-spring-damper primitive `spring()`:
     ```typescript
     config: { damping: 12, mass: 0.5, stiffness: 110, overshootClamping: false }
     ```
  2. Implement organic overshooting on bar reveals, metric tickers, and delta callout badges.

### Objective 7.2: Layered Dark Glassmorphism Theme Overhaul
* **Problem Statement:** Pure `#000000` canvas with harsh neon green `#39FF14` and Linux system font `DejaVu Sans` feels dated.
* **Technical Specification:**
  1. Adopt modern layered dark-mode palette in `pipeline/animations/src/theme.ts`:
     * Background Canvas: Deep Midnight Slate (`#0B0F19` with subtle radial vignette to `#030712`).
     * Card Panels: Translucent frosted glass (`rgba(17, 24, 39, 0.75)` with `backdrop-filter: blur(16px)` and `1px solid rgba(255, 255, 255, 0.10)`).
     * Accents: Cyber Yellow (`#FFE600`) for active highlights, Tech Cyan (`#00F2FE`) for winning benchmark bars, Emerald (`#10B981`) for positive deltas.
  2. Migrate typography to geometric Google fonts: `Montserrat ExtraBold` (headers), `Inter Black` (body), and `JetBrains Mono` (tabular numbers).

### Objective 7.3: 3D Perspective Tilt TweetCard & Animated SVG Highlighter
* **Technical Specification:**
  1. Update `pipeline/tweet_card.py` and Remotion TweetCard component with 3D entry physics:
     * Entrance perspective: $\text{rotateX}(8^\circ) \to \text{rotateX}(0^\circ)$ with smooth spring dampening.
     * Subtle floating hover oscillation ($\pm 3$px vertical sine wave).
  2. Add an animated SVG yellow highlighter pen stroke (`stroke-dashoffset` animation) drawing across key tweet phrases at second 1.2.

### Objective 7.4: Automated Transition Sound Effects (SFX)
* **Technical Specification:**
  1. Curate CC0 / royalty-free micro-sound effects in `pipeline/assets/sfx/`:
     * `whoosh_subtle.wav` (-18 dB): Synchronized with visual shot cuts.
     * `click_pop.wav` (-15 dB): Synchronized with metric counter milestones and bar chart completions.
     * `bass_drop.wav` (-12 dB): Synchronized with hero benchmark reveals.
  2. Update `pipeline/assemble.py` to automatically calculate shot boundary timestamps and mix SFX audio cues into the master soundtrack.

### Objective 7.5: Pre-Bundled Remotion Webpack Caching
* **Problem Statement:** `pipeline/animations/render.mjs` bundles Remotion Webpack from scratch on every shot invocation (`bundle(entryPoint)`), incurring 4–8 seconds of redundant compilation overhead per shot (~25–35s per video).
* **Technical Specification:**
  1. Implement disk bundle caching in `pipeline/animations/render.mjs`: store `bundleLocation` in `.remotion_bundle_cache/` keyed by hash of `src/` and `package.json`.
  2. Re-use the existing pre-bundled bundle across all shots in a run, reducing total rendering time by **~25–35 seconds per video**.

### Phase 7 Exit Criteria — ALL COMPLETE ✅
- [x] Remotion compositions utilize spring physics with organic bounce and modern glassmorphic styling (`BenchmarkLadder`, `ArchitectureDiagram`, `KineticMetricCounter`).
- [x] 3D TweetCard with perspective entry tilt (`rotateX(8°)`), floating hover oscillation, and animated SVG highlight pen verified.
- [x] Transition SFX (whooshes, UI pops, bass drop) automatically synthesized locally ($0 cost) and mixed at cut boundaries in `pipeline/assemble.py`.
- [x] Webpack bundle caching active in `render.mjs`, eliminating redundant bundling latency.
- [x] Full regression test suite passes cleanly (54 passing tests) and flagship clip verified live on Telegram review queue.

---

## 9. Future Horizons & Backlog (Paused Subsystems)

The following capabilities are maintained in the codebase in a paused state and will remain inactive until prioritized:

| Subsystem | Original Job / Location | Re-Activation Prerequisites |
|---|---|---|
| **Daily 5-Story Digest** | `crons/muse-video-pipeline-daily` | Lock finds clip performance and audience retention before resuming high-cadence 5-story daily cuts. |
| **Daily X News Scan** | `crons/x-news-daily-scan` | Resume in tandem with the daily 5-story digest to pre-populate daily candidates. |
| **Rumors Digest** | `crons/rumors-digest-daily-6am` | Evaluate audience interest in unconfirmed leaks vs verified finds. |
| **Weekly 16:9 Long-Form** | `pipeline/run.py --mode weekly` | Deferred until 9:16 vertical short-form workflows and brand positioning are fully established. |
| **Direct API Publishing** | `pipeline/publish.py` | Resume only after official TikTok Developer app audit and YouTube OAuth production verification. |

---

## 10. Operational Summary & Implementation Sequence

The roadmap now encompasses the complete journey from initial environment bootstrapping to scaling TikTok reach:

```
[Phase 1: Bootstrapping & Spikes] ✅ COMPLETE
  └── .venv, Torch CPU, Kokoro offline cache, 2x dark-mode tweet cards

[Phase 2: Core Engine & Remotion] ✅ COMPLETE
  └── Free X search, Remotion animation engine, Declarative Clip Assembler

[Phase 3: Scorecard & Cloud Crons] ✅ COMPLETE
  └── 4-Pillar Scorecard, 4 daily Cloud Crons deployed with silent exit contract

[Phase 4: Validation & Cutover] ✅ COMPLETE
  └── Blocking Clip QA gate, live Telegram queue delivery, 41/41 tests passing

[Phase 5: Safe-Zone & Quick Wins] ✅ COMPLETE
  └── Captions to y=1180, qa.py safe-zone update, ducked music bed, curiosity hooks

[Phase 6: $0 Studio Voice & Pacing] ✅ COMPLETE
  └── Google Cloud Studio TTS via Google AI Pro ($0 spend), bouncing captions, 2.0s ASL

[Phase 7: Production Polish & Springs] ✅ COMPLETE
  └── Remotion spring physics, 3D TweetCard, transition SFX, Webpack bundle caching
```


