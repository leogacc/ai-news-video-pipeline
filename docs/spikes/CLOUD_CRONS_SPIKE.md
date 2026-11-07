# Spike Report: Cloud Crons Platform Evaluation & Scheduling Architecture

**Document ID:** SPIKE-2026-CLOUDCRONS  
**Status:** Complete  
**Date:** 2026-11-06  
**Author:** Antigravity  
**Goal Reference:** Phase 1.3 — Cloud Crons Platform Evaluation Spike (`docs/ROADMAP.md`)  
**Target Delivery:** Phase 2.1 & Phase 2.2 Operational Scheduling  

---

## 1. Executive Summary

As directed by the Creative Director:
> *"you antigravity will do this in cloud crons instead"*
> *"we'll stop using threads. lets figure out how to search X for free"*

This investigation evaluated and benchmarked the execution platforms available to automate the pipeline's **4x-daily finds scout schedule** (07:00, 11:00, 16:00, 19:00 Pacific). The scout must reliably ingest public X announcements and news, filter candidates through the **TikTok Excitement Gate** (*"entertaining & educational, high-stakes, broad public appeal"*), synthesize voiceovers with Kokoro-82M TTS, capture high-res Chromium screenshots or Remotion animations, and publish reviewed candidates to Telegram.

Three candidate platforms were evaluated:
1. **Option A: GitHub Actions Scheduled Workflows (`.github/workflows/daily.yml`)**
2. **Option B: Antigravity Cloud Crons (`crons/*.md` platform tasks) — [SELECTED WINNER]**
3. **Option C: Dedicated Headless Cloud Runner (systemd timers / host cron daemon)**

### Key Decision & Verdict
* **Winner: Option B (Antigravity Cloud Crons)** is selected as the primary production orchestration engine.
  * **Zero Cold-Start:** Complete pipeline execution environment starts in **3.68 seconds** (73x faster than GitHub Actions' 4.5-minute VM provisioning).
  * **Pre-Warmed AI Models:** Local caches for Kokoro-82M TTS and OpenCV YuNet face detection are pre-loaded, enabling sub-2s inference without HuggingFace network bottlenecks.
  * **Agentic Excitement Gate:** Employs AI agent reasoning during scheduled runs to rigorously evaluate whether candidate posts meet the user's high editorial bar (*"must be worth making a TikTok about"*), skipping routine, incremental, or uninspiring stories automatically.
  * **Isolated Secret Storage:** Production tokens reside securely in `.env` with strict `0600` permissions.
* **Option A (GitHub Actions):** Retained strictly as a manual fallback dispatch mechanism (`workflow_dispatch`), disabled for scheduled runs due to cold-start penalties and cron schedule jitter.
* **Option C (Dedicated systemd):** Redundant in containerized agent environments and lacks agentic evaluation capability.

---

## 2. Evaluation Matrix

| Evaluation Dimension | Option A: GitHub Actions | Option B: Antigravity Cloud Crons (Selected) | Option C: Headless systemd / Daemon |
| :--- | :--- | :--- | :--- |
| **Cold-Start Provisioning** | 240–300s (installs Python, Torch CPU, Kokoro, Chromium) | **3.68s (all venv dependencies pre-warmed)** | ~3.5s |
| **Model Weight Caching** | Must pull ~300MB weights from cache/HuggingFace each run | **Pre-cached locally (`~/.cache/huggingface/hub`)** | Pre-cached locally |
| **Editorial Curation (TikTok Gate)** | Brittle regex / script heuristics only | **Agentic reasoning (deep context & taste alignment)** | Script heuristics only |
| **Screenshot Engine** | Requires xvfb / headless Chromium CI setup | **Native Node 24 + Chromium (`render.mjs`) ready** | Native Node + Chromium |
| **Credential Security** | GHA repository secrets (risk of CI log leakage) | **Local `.env` (`0600` unix permissions)** | Local `.env` file |
| **Schedule Precision** | Jitter of ±15–45 minutes during peak UTC load | **Deterministic cloud scheduling** | Second-level precision |
| **Concurrency & State Handling** | Requires git commit & push from runner (merge conflicts) | **Local atomic writes (< 4ms) to state files** | Local file writes |
| **Verdict** | Manual Fallback Only | **PRIMARY PRODUCTION ORCHESTRATOR** | Disqualified |

---

## 3. Live Benchmark Results

Tests executed on November 6, 2026, using `scout/spike_cloud_crons.py`. Raw dataset recorded in [`scout/spike_crons_results.json`](file:///home/antigravity/leogacc/ai-news-video-pipeline/scout/spike_crons_results.json).

### 3.1 Environment Warm-Start Latency

| Subsystem / Dependency | Import Latency (Antigravity Cloud VM) | Estimated GHA Cold Start | Speedup Factor |
| :--- | :--- | :--- | :--- |
| `PIL` (Pillow 13.0) | 0.0118s | ~12.0s | ~1,000x |
| `cv2` (OpenCV Headless) | 0.0679s | ~18.0s | ~265x |
| `torch` (PyTorch 2.15.0+cpu) | 0.9283s | ~90.0s (download + wheel install) | ~97x |
| `av` (PyAV pinned 16.1.0) | 0.0387s | ~15.0s | ~387x |
| `kokoro` (TTS Engine & Tokenizer) | 2.6365s | ~135.0s (pip + weights download) | ~51x |
| **Total Pipeline Warm Start** | **3.683s** | **~270.0s (4.5 minutes)** | **73.3x Speedup** |

### 3.2 Secret Resolution & Isolation

* **File:** `.env` located at project root.
* **Unix Permissions:** `0600` (`-rw-------`), non-world-readable.
* **Keys Verified Active:**
  * `TELEGRAM_BOT_TOKEN`: Authenticated to `@aividpipBOT`.
  * `TELEGRAM_CHAT_ID`: `1904835992` (verified via live test ping).
  * `PIXABAY_API_KEY`: Authenticated (HTTP 200).

### 3.3 State Deduplication & Concurrency

Measures read and atomic write latencies across pipeline state databases:

| State Database | File Size | Item Count | Read Latency | Atomic Write Latency |
| :--- | :--- | :--- | :--- | :--- |
| `scout/state.json` | 40.5 KB | 6 key categories | 0.17 ms | 0.78 ms |
| `scout/saved_items.json` | 254.7 KB | 520+ saved items | 2.50 ms | 3.93 ms |
| `scout/clipped_finds.json` | 51.4 KB | 48 clipped records | 0.27 ms | 0.88 ms |

* **Integrity:** State writes use atomic staging via tempfile replacement, preventing JSON corruption if a run is interrupted.

### 3.4 Offline AI Model Cache Readiness

* **Kokoro-82M TTS:** Weights and tokenizer cached in `~/.cache/huggingface/hub/models--hexgrad--Kokoro-82M`. Instantaneous pipeline initialization (**1.66s**), operating offline without network token dependence.
* **OpenCV YuNet Face Detector:** `pipeline/cache/models/face_yunet.onnx` verified (227.1 KB binary, SHA256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`).
* **Chromium Rasterization Engine:** Headless Chromium warm start verified at **1.50s** for full-resolution rendering.

---

## 4. Architectural Decision Record (ADR)

### ADR-2026-03: Selection of Antigravity Cloud Crons as Scheduled Runner

* **Context:** The pipeline requires 4x-daily automated execution (07:00, 11:00, 16:00, 19:00 PT). Legacy workflows in GitHub Actions suffer from prohibitive cold-start times (4.5 min) and lack contextual awareness, while legacy cron definitions in `crons/` contained obsolete paths and deprecated Threads instructions.
* **Decision:** We establish **Antigravity Cloud Crons** as the sole automated production scheduler.
* **Execution Contract:**
  1. **Schedule:** 4 runs daily at `07:00`, `11:00`, `16:00`, `19:00` Pacific (`America/Los_Angeles`).
  2. **Ingestion & Curation:** The worker executes Phase 2.1 Free X Search (`pipeline/x_search.py`), scans the 14 VIP accounts, and searches Google News RSS for AI keyword dispatches.
  3. **TikTok Excitement Gate:** Every post is evaluated against the Creative Director's strict editorial bar:
     * *Pass:* High-stakes, surprising capability, visceral demo, broad public appeal, entertaining & educational.
     * *Fail (Skip):* Incremental benchmark updates, routine plugin announcements, company hardware spec-bumps without capability shifts, legal/copyright lawsuits.
  4. **Silent Notification on Below-the-Bar Runs:** If no post clears the bar, the cron ends silently without sending empty pings to Telegram, reserving alerts strictly for high-value candidates.
  5. **Visual Asset Assembly:** Approved candidates generate 2x dark-mode cards via `pipeline/tweet_card.py` and download broadcast 1080p MP4s from `video.twimg.com`.
  6. **Publishing:** Dispatches sent to Telegram review chat via `@aividpipBOT`.

---

## 5. Modernized Cron Specifications

All four cron job definitions in `crons/` are updated to match this specification:
* `crons/x-scout-finds-7am__daily@07:00:00.md` (07:00 PT)
* `crons/x-scout-releases-rumors__daily@11:00:00.md` (11:00 PT)
* `crons/x-scout-finds-4pm__daily@16:00:00.md` (16:00 PT)
* `crons/x-scout-finds-7pm__daily@19:00:00.md` (19:00 PT)

Each task file has had all Threads references expunged, workspace paths pointed to `/home/antigravity/leogacc/ai-news-video-pipeline/`, and instructions wired directly to the Phase 2.1 Free X Search architecture.
