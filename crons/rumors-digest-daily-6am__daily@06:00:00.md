---
id: rumors-digest-daily-6am
title: Rumors digest (daily 6am)
enabled: false
owner: goal:ai-news-video-pipeline
mode: task
schedule:
  kind: daily
  timezone: America/Los_Angeles
  time: 06:00:00
delivery:
  - chat_id: 33ba1f16-92ad-48c4-a1de-c405bf6033ef
metadata:
  originating_chat_context_json: '{"chat_id":"33ba1f16-92ad-48c4-a1de-c405bf6033ef","origin_provider":"main","chat_kind":"direct","event_kind":"message","require_mention":false,"device_id":"84a676f618d085c4"}'
  presentation_locale: en-US
---
DAILY RUMORS DIGEST — 6:00am PT every morning (user, 2026-10-25 22:02 PT).

Build the top-3 AI rumors digest video (rumors template) and publish it to the Telegram review queue, then report in this chat. Delivery: this side chat.

SOURCE OF TRUTH (read first):
- ~/workspace/ai-video-pipeline/scout/saved_items.json — all rumors; downstream reads this file first.
- ~/workspace/ai-video-pipeline/scout/state.json — posted_rumor_ids and other dedupe state.
- Template: ~/workspace/ai-video-pipeline/templates/rumors-digest/template.yaml, plus the 2026-10-25 fixed-version standards below.

SELECTION (user rule, 2026-10-25 22:02 — this SUPERSEDES the old fresh-only gate, which required 3 unposted rumors or nothing):
1. Fresh first: distinct unposted rumors, most-interesting-first. A Threads post mirroring an already-saved X post is coverage only and NEVER counts as a distinct rumor. Leaks count as rumors (user 2026-10-26): leaked models, documents, benchmarks, or internal information are eligible rumor stories — unconfirmed by definition; label them RUMOR (and as a leak where that is what it is) with source account and date, never as confirmed. Scout runs should likewise classify leaked material as rumor when saving to the pool.
2. If fewer than 3 fresh, fill to 3 with OLDER ACTIVE rumors: rumors covered before that are STILL unconfirmed and still relevant. Verify each reused rumor is still active with a quick search (not confirmed, released, or debunked since it was covered); NEVER reuse a resolved or expired rumor.
3. Rotate: when alternatives exist, do not repeat the exact same trio as the previous digest; prefer older actives not used in the most recent digest.
4. STILL NEED 3 TOTAL: if fresh + older active < 3, render NOTHING (no 1-2 rumor version, no format adaptation, nothing to Telegram). Report HELD in chat with the counts and why.
5. Label honestly: reused rumors are marked on screen (bio) and in the description as ONGOING — still unconfirmed and previously covered — never presented as fresh. Fresh rumors are labelled RUMOR with source account, date, and "not confirmed", as usual.

BUILD (same as the 2026-10-25 rumors digest, fixed version):
- New run folder pipeline/output/scout/rumors/<YYYYMMDD>/; script.json (3 hooks + self-plug branding line + 3 deep dives, most-interesting-first, Flesch-Kincaid ≤ 9.5, 180-270 words), Kokoro am_echo 1.20x, music OFF, 1080x1920 30fps H.264 High L4.0 yuv420p faststart, −14 LUFS.
- Number pills EXACTLY the daily pill (138x66 flat dark (24,24,24) alpha 128, 24px transparent margin, mask radius 18 blurred 14, 42pt white text, rect x813..951 y179..245, format n/3).
- Captions: terminal green per-letter typewriter, on a SOLID BLACK caption bar y1500..1920 on every frame (bio ends at 1500, untouched).
- Brand segment: Pixar self-plug montage exactly like the daily digest (portrait rows in story order, CEO rule — a company story's character is that company's CEO; characters left, company logos right, slide then full split hold). NEVER the old blurred triptych. Build with a rumors-specific script; NEVER overwrite pipeline/cache/verified/intro_people.png (the daily portrait).
- Watermark @leos.logos every frame (34pt, white 50%, x60 y190; y80 on dive frames only).
- QA before publish: ffprobe clean, loudness −14 LUFS, full decode, no black segments, shot-by-shot frame review (pill, captions on black, Pixar brand, no overlaps). A render counts as done only once it is in the Telegram review queue.

CONCURRENCY (standing rule): never leave multiple renders in flight. If the daily pipeline (18:00 PT) or another scout run is rendering, WAIT (max 60 min) for it to finish; never build over another render. At 6am this should be clear, but check before rendering.

PUBLISH + REPORT:
- Telegram review queue: video + TikTok description (3 clauses, 1-2 questions on rumor #1, sources/dates/links, fresh vs ongoing marked, exactly 5 hashtags as the final line, never claim to be an AI, never present rumors as confirmed). Use pipeline/publish.py telegram_send + telegram_send_description.
- Update scout/state.json posted_rumor_ids with the fresh rumors used (reused older actives stay posted; do not duplicate ids). Record the run (fresh count, reused count, held or sent) in state.
- Chat report, kept short: built + sent (the 3 rumors, noting which were fresh vs ongoing), or HELD (counts + why).
