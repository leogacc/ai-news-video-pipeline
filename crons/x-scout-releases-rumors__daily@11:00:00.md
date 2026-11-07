---
id: x-scout-releases-rumors
title: 'Finds scout: one top find clip (11am)'
enabled: true
owner: goal:ai-news-video-pipeline
mode: task
schedule:
  kind: daily
  timezone: America/Los_Angeles
  time: 11:00:00
timeout_secs: 7200
delivery:
  - chat_id: 33ba1f16-92ad-48c4-a1de-c405bf6033ef
metadata:
  originating_chat_context_json: '{"chat_id":"33ba1f16-92ad-48c4-a1de-c405bf6033ef","origin_provider":"main","chat_kind":"direct","event_kind":"message","require_mention":false,"device_id":"84a676f618d085c4"}'
  presentation_locale: en-US
---
FINDS SCOUT — 4x daily (7am, 11am, 4pm, 7pm Pacific). This job is the 11am run; the 7am, 4pm and 7pm runs are separate schedules with an identical body. All four share the same state files, so each run must re-check dedupe before picking. Separate from the daily digest scan (17:00 PT) and the daily pipeline run (18:00 PT). Do not touch daily digest outputs, daily script, or daily state except to READ pipeline/state.json posted_ids for dedupe.

SETUP FIRST: Read scout/README.md, scout/accounts.yaml, scout/keywords.yaml, scout/clipped_finds.json, and templates/clips/template.yaml in full before doing anything else. The README's "Hourly finds mode" section (now 4x-daily mode) and "Dedupe and the major-progress exception" section govern this run.

SOURCES — 100% FREE X DISCOVERY & INGESTION (THREADS DECOMMISSIONED):
- VIP Accounts: scout ONLY the accounts listed in scout/accounts.yaml via the official Twitter Syndication Timeline API (https://syndication.twitter.com/srv/timeline-profile/screen-name/<handle>). NEVER guess accounts, and NEVER scout accounts you think are relevant but are not listed.
- Keywords: run the combined search_queries in scout/keywords.yaml via Google News RSS (https://news.google.com/rss/search?q=site:x.com+<query>), searching back UP TO 3 MONTHS — not just since the last run. A keyword hit is NOT a story by itself — it must be a notable post with source post + date + author. Skip hype, memes, and engagement bait, and log why in the run report.
- Single Post Hydration: hydrate any candidate post via the official Twitter Syndication CDN (https://cdn.syndication.twimg.com/tweet-result?id=<id>&token=x) to extract verified status, true engagement metrics, full photo galleries, and direct 1080p MP4 broadcast URLs (from video.twimg.com).
- Threads is PERMANENTLY DECOMMISSIONED. Do NOT search Threads, do not run threads-cli, and do not reference threads.yaml.
- If NO source can be read at all, report "scout not configured" and STOP. Do not publish anything, do not build anything, do not guess.

EACH RUN:
1. Scout VIP accounts (in order listed in scout/accounts.yaml) and keyword queries on X via Google News RSS, collecting notable AI finds from up to 3 months back.
2. Classify each new notable post as RELEASE, RUMOR, or FIND, in plain words in your report:
   - RELEASE: official announcement — product/model launch, company post, confirmed feature, paper/demo from the lab itself.
   - RUMOR: unconfirmed — leak, "reportedly", "sources say", leaker/reporter post, no company confirmation yet.
   - FIND: GENERAL AI finds — community tools, demos, projects, research, benchmarks, clever uses that are real and demonstrable (repo, code, or demo linked), but neither an official release nor a future rumor. Do NOT call this category Hacks, and do NOT use hack-specific terms (jailbreak, unlock, crack, bypass) as primary search terms. If a find happens to be an unlock or workaround, label its benchmarks as claimed by its author, describe it neutrally, and never give steps for bypassing, unlocking, or reverse-engineering anything.
   - If neither notable nor clearly classifiable, skip it and log why, not in a video.
3. SAVE EVERYTHING FIRST, before building any video: append each classified item to scout/saved_items.json with post_id, author, date, text, url, category (release/rumor/find), source (account/keyword + which account or query), and any verified link (repo, announcement page). This saved pool is what downstream pipelines read. Rumors found here are saved only (the rumors digest handles them). RELEASES ARE PART OF FINDS (user, 2026-10-26): a release is eligible to be picked and clipped exactly like a find, and releases are also eligible for the daily digest.
4. PICK ONE TOP FIND OR RELEASE, and only one: rank the eligible FINDS and RELEASES by how notable and interesting they are, most interesting first — judged by what is most interesting, pressing, exciting, or important for the AVERAGE INTERESTED PERSON (broad appeal beats a technically neat but narrow find) — RECENCY IS ONLY A TIE-BREAKER, not the ranking. A find or release from weeks or months ago (up to 3 months back) that was never clipped is fully eligible if it is the most interesting unclipped find or release. It must have a verified link or demonstrable demo. If no find or release clears that bar, build nothing, clip nothing, and end the run silently (update state and saved_items only). Never invent a find to fill a run, never clip two finds or releases in one run.

EXCITEMENT GATE (user, 2026-10-27, 2026-11-05): "exciting" is a strict GATE — MUST BE WORTH MAKING A TIKTOK ABOUT (entertaining and educational). Evaluated via the Codified TikTok Worthiness Scorecard (scout/README.md, scout/x_scout.py:excitement_gate_score). A top pick must score >= 28 / 40 total, with no individual pillar below 6 / 10.
- Routine, incremental, or "company X adds Y support" stories do NOT clear the bar (e.g. 2026-10-27 ChatGPT iCloud Mail/Calendar plugins).
- Product and hardware launches do NOT clear the bar even when first-in-category without a surprising capability or stakes beyond the product itself (e.g. 2026-10-28 XREAL Aura XR glasses).
- Legal-dispute stories do NOT clear the bar on scale or stakes alone (e.g. 2026-11-02 NYT v Brave).
If no candidate clears the gate, build nothing and end the run silently — never fill a run with a routine story.

AUTOMATED EXECUTION:
Run the production scout orchestrator directly:
`.venv/bin/python3 scout/x_scout.py --run-cron`

This command executes the full operational contract:
1. Ingests candidate posts across VIP timelines (scout/accounts.yaml) and Google News RSS keywords (scout/keywords.yaml).
2. Persists items to scout/saved_items.json and updates seen IDs.
3. Evaluates candidates through the 4-Pillar TikTok Worthiness Scorecard (scout/README.md, score >= 28/40, all pillars >= 6).
4. Silent Exit: If no candidate achieves >= 28/40, ends the run silently without pinging Telegram.
5. Clip Assembly & Delivery: If a candidate passes, builds the vertical clip via pipeline/assemble.py (Dynamic Hug, Kokoro am_echo TTS, Remotion animation/card, ASS captions, -14 LUFS loudnorm) and pushes video + TikTok description to @aividpipBOT.

5. DEDUPE before building anything: check scout/state.json (seen_post_ids, posted_release_ids, posted_rumor_ids, posted_find_ids), scout/clipped_finds.json (every previously clipped find), AND pipeline/state.json posted_ids. A post already CLIPPED or POSTED is never rebuilt — EXCEPT the major-progress exception: a re-clip of a previously clipped find is allowed ONLY when you can document a substantive new development (a new major version or official release superseding the demo, a materially changed capability or benchmark, or confirmation/adoption that changes the story — NOT a repost, an engagement bump, a minor bugfix, or the same claims restated). A major-progress re-clip must be labelled as an update in its description ("Update on X — previously clipped on <date>"), must say what is new versus the previous clip, and must be appended to scout/clipped_finds.json as an update entry against the original post_id. Being merely SEEN before does not block a pick, but a find previously skipped for a recorded substantive reason (unverifiable, not demonstrable, hype/engagement bait) stays skipped unless new evidence changes that. Update scout/state.json with seen/posted ids and last_scout_run after each run, and append every new clip to scout/clipped_finds.json.

6. BUILD THE CLIP following templates/clips/template.yaml in full: transcript scan, speaker scan, title + same-length bio block, per-speaker face check (move text a little lower if it hits a face), no-face layout when there is no face, full video uncut when information-dense throughout, otherwise the single most interesting part. Title/bio placement follows lower-thirds craft: two lines only, name dominant over role, text on its own backing, band lifted above the bottom UI zone on a 9:16 frame, and the dwell frame verified by stills before shipping.
   - Visual Assets: Render high-fidelity 2x dark-mode card via pipeline/tweet_card.py (with gold/blue verified badge, engagement metrics, media grid). If the post has a video, download the highest-bitrate MP4 directly from video.twimg.com. If an abstract research paper or find lacks native video, generate a dynamic visual animation via the Remotion engine (pipeline/animations/).
   - Layout & Styling: Dynamic Hug geometry (content centred on black, title directly above, bio directly below with 20px gaps; bio is single regular line "Source: <root>, <date>", @leos.logos watermark at 20% opacity beneath bio, terminal green captions top-anchored at ~y1530).
   - Audio / Narration: If the post has no native audio/video, narrate via Kokoro am_echo at 1.20x from verified facts only (no invented claims). BIO SOURCE RULE: bio line names the ROOT source (company announcement, paper, repo), NEVER the surfacing post.
   - Output: pipeline/output/scout/clips/<date>_<slug>/, one folder per clip (video + transcript + meta). QA clean before publish.

7. PUBLISH to Telegram review queue via pipeline/publish.py: sends candidate clip with description to @aividpipBOT review chat.
8. REPORT to the user in this chat ONLY when a clip was published: the find, why it topped the run, the clip link, its source, and anything skipped + why. On runs with no new top find, stay silent — do not send a "nothing new" message. If an account or query could not be read, report that error with the next published clip.
9. CONCURRENCY: never leave multiple scout runs in flight, and never run a clip build at the same time as the daily pipeline render (18:00 PT) or another scout run. If a previous scout run or the daily pipeline is still rendering, do a save-only pass this run (steps 1–3 and 5) and skip the build — the find stays in the saved pool for the next run's pick.

Do not edit MEMORY.md. Log observations in scout/state.json, scout/clipped_finds.json, scout/saved_items.json, and in the run report only.
