# Rumors Digest

Copy of the Daily Digest template, adapted for the X scout cron, for
rumors only.

Differences from Daily Digest:
- **3 stories, not 5** — top 3 rumors, most-interesting-first
- **Number pills are n/3**, not n/5
- **Self-plug says “top three AI rumors digest”**, montage is 3 rows max
  or omitted if no central persons are verified
- **Every rumor is labelled as a rumor** on screen and in the description,
  with its source account, post date, and what is actually claimed —
  never presented as a confirmed release
- **Voice is the same** as Daily Digest: Kokoro `am_echo` at 1.20×, music off

Confirmed releases do NOT go in this digest — they go to clips, one clip
per release, following `templates/clips/template.yaml`.

Status: draft, created 2026-10-24 for the scout cron. No pipeline code
change was made with this template, and no run is wired to it yet.
