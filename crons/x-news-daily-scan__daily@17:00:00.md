---
id: x-news-daily-scan
title: Daily X news scan for video pipeline
enabled: false
owner: goal:ai-news-video-pipeline
mode: task
schedule:
  kind: daily
  timezone: America/Los_Angeles
  time: 17:00:00
delivery:
  - chat_id: 33ba1f16-92ad-48c4-a1de-c405bf6033ef
metadata:
  originating_chat_context_json: '{"chat_id":"33ba1f16-92ad-48c4-a1de-c405bf6033ef","origin_provider":"main","chat_kind":"direct","event_kind":"message","require_mention":false,"device_id":"84a676f618d085c4"}'
  presentation_locale: en-US
---
Daily X/Twitter AI-news scan feeding the video pipeline. X has no free search API, so this scan runs through web search (which surfaces viral X posts and news about X discussions) and writes the top stories as curated input for the pipeline's scout stage.

SCHEDULE (2026-10-20, user — supersedes the 03:00 PT scan): this scan fires daily at 17:00 PT, one hour before the 18:00 PT pipeline run, so the evening run covers that same day's news.

SOURCE CHECK (2026-10-22, user — after the Claude Duet miss): the Oct 21 Duet launch was broken by Reuters, MacRumors, and 9to5Mac before it trended on X, and the 17:00 scan missed it entirely. Every scan must ALSO run site-scoped searches over those outlets for the day's AI announcements — e.g. site:reuters.com AI, site:macrumors.com AI, site:9to5mac.com AI — in addition to the queries below. A major launch on any of these outlets counts as a top story even if it has no X traction yet. This check is permanent, not a one-off.

Each run:
1. Use `browser.search` (news vertical) with these queries (all of them, every day):
   - "AI news X post" / "artificial intelligence announcement twitter" (X-origin stories)
   - "AI Twitter viral today" (what's being discussed)
   - BACKSTOP (mandatory): "biggest AI news today" and "OpenAI Anthropic Google AI announcement" — catches major stories even if they didn't originate on X. A story as big as OpenAI's Oct 6 release of 722 AI-generated math proofs must never be missed again: if the single biggest AI story of the last 24h isn't already in your picks, add it.
2. Pick the 4-6 strongest AI stories from the last ~24h. Rank by real-world significance first, X-connection second. For each, write a 2-3 sentence summary grounded ONLY in what the search results establish (who posted/announced what, key facts, reaction). Never invent specifics. Prefer results with a direct x.com post link as the story URL; otherwise use the best news article URL.
3. For EACH story, also try to find one relevant X post containing a video or striking image (e.g. the official announcement post, a demo clip). Record its direct x.com post URL as `x_media_url`. If none is clearly found, omit the field — never guess URLs.
4. Write `~/workspace/ai-video-pipeline/pipeline/input/x_curated.json`:
   {"stories": [{"title": ..., "summary": ..., "url": ..., "source": "X via @handle or outlet", "x_media_url": "<x.com post url or omit>", "added_at": "<now in UTC ISO format>"}, ...]}
   Keep 4-6 stories. Titles under 120 chars.
5. Push the file to the repo so the 18:00 PT pipeline run picks it up: use `~/workspace/skills/github/.venv/bin/python ~/workspace/skills/github/bin/gh.py` — inline python importing `put_file` and `req` from `bin/gh.py` (read the current skill at `~/workspace/skills/github/SKILL.md` first if unsure of the pattern; fetch the file sha via GET on 422 and retry). Commit message: "daily X news scan YYYY-MM-DD".
6. If fewer than 2 solid stories are found, still write the file with what you have (even 1 story, or an empty stories list) — do not pad with weak items.
7. Stay silent on routine successful runs. Message the user only if the scan or push fails in a way that needs them (e.g. repo access broken).

The pipeline's ingest.py already loads `pipeline/input/x_curated.json` as curated stories (freshness window 36h), and visuals.py uses each story's `x_media_url` (or x.com story URL) to pull the post's own video as b-roll. This file is consumed automatically by the daily 18:00 PT run. Do NOT dispatch pipeline runs from this job.
