

# Pipeline Upgrade Flow

## Purpose

A pipeline upgrade is not done when the code is edited. It is done when it is
**saved as a new version that every run uses**. On 2026-10-12 a whole day of
upgrades went missing from the daily video because the cron instruction file
was edited directly — which does not update the scheduler's saved job
definition. This skill exists so that never happens again.

## The pipeline has three layers — upgrade the right one, then version it

1. **Code** (`~/workspace/ai-video-pipeline/pipeline/*.py`) — rendering,
   captions, visuals, analytics, QA. Changes here apply to every run
   automatically once saved.
2. **Worker instructions** (the `muse-video-pipeline-daily` cron job body) —
   what the 03:45 worker does: curation, scriptwriting, pin verification,
   frame review. Changes here ONLY take effect via `cron.update`.
3. **Assets** (`pipeline/cache/verified/`, `pipeline/cache/generated/`) —
   pins, portraits, clips. Regenerated per run; not versioned.

## Upgrade steps (all of them, every time)

1. **Implement the change** in the right layer. Follow the user's root-cause
   standard: fix the pipeline, not one render.
2. **Verify it works** — run the affected stage or a full render; do not
   claim an upgrade that hasn't rendered.
3. **Bump `pipeline/VERSION`** — date-based: `YYYY.MM.DD.N` (N increments
   within a day). One line, no extra text.
4. **Append `pipeline/CHANGELOG.md`** — newest entry first: version, date,
   what changed and why (one line per change, plain mechanics).
5. **If worker instructions changed: `cron.update`** with the complete
   revised body (copy it from the current cron .md file, applying your
   edits there first if needed), then **`cron.view` to verify** the saved
   definition actually contains the new text. NEVER edit the cron .md file
   directly and stop there — the scheduler ignores file edits.
6. **Confirm the version stamp**: `run.py` prints `[run] pipeline version X`
   and stamps `pipeline_version` into `qa.json` after the qa stage. Check
   the latest `qa.json` to prove which version built a video.
7. **Report**: the new version number + what changed, in one short message.

## Diagnosing "the video is missing our upgrades"

1. Check `qa.json`'s `pipeline_version` — which code built it?
2. Check `pipeline/VERSION` — is the upgrade actually saved and versioned?
3. If the missing upgrade was a worker-instruction change: `cron.view` the
   job and grep the body for the rule. If it's absent there but present in
   the .md file, the job was edited without `cron.update` — re-sync it.
4. If the code has the upgrade but the video doesn't show it: check whether
   the run actually executed that code path (trace log), and whether cached
   assets (pins, portraits, clips) were regenerated.

## Rules

- No silent upgrades: every change gets a version bump + changelog entry.
- No file-only cron edits. Ever.
- The daily worker, the watchdog, and manual renders all read the same
  `pipeline/` checkout and the same saved cron definition — that is what
  "everyone uses" means. There is no second copy to sync.
## Available connectors

Use `muse.connector_search` to find the current connector docs before following
recovered instructions.
