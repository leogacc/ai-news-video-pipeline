# Pipeline changelog

Every pipeline upgrade bumps `VERSION` and adds an entry here, newest first.
The version is stamped into every render's `qa.json` (`pipeline_version`)
so any video can be traced to the exact code that built it.

## 2026.10.13.1 — 2026-10-13
- Landscape mode (user): new 16:9 `landscape` config mode (1920x1080) and
  render path, developed on the `landscape-layout` branch. Story
  deep-dives split the frame — left third is a live terminal panel typing
  the narration in green mono synced to TTS word timings (this IS the
  caption track in landscape; no ASS captions burned), right two-thirds
  plays the visual. Intro/hooks/branding stay full-frame: wide terminal
  intro, side-by-side person+logo hook pairs (new
  `hook_pair_<sid>_landscape.png`, cache-safe alongside the 9:16 pairs),
  pillarboxed self-plug. Story badge top-right of the visual region,
  watermark top-left of the visual region, hook number pills centered on
  the badge. Story emphasis pills skipped in landscape (the panel shows
  the text). QA safe-area check is mode-aware (YouTube zones: top 70px,
  right 40px, bottom 7%). Render writes `chapters_landscape.txt` (YouTube
  description chapters). Two-up render support: a shot with
  `two_up`/`path2` shows both visuals side by side in the visual region
  (data contract documented; worker markup pending). The 9:16 daily path
  is untouched.

## 2026.10.12.3 — 2026-10-12
- Story ordering rule change (user): most interesting/important story
  FIRST — supersedes the 2026-10-11 smallest-first crescendo rule.
  Headline hooks, story numbering (#1–#5), and deep dives all follow the
  same descending order; #1 is the story viewers most need to see.
  Implemented in the daily cron worker instructions (via cron.update +
  cron.view). Takes effect on the next scheduled run (2026-10-13 03:45 PT).

## 2026.10.12.2 — 2026-10-12
- A/V sync root-cause fix (render.py): no-loop clips (self-plug,
  analytical animations) played ONCE via `-t {dur}`, but ffmpeg's `-t`
  is a cap, not a pad — the self-plug clip (5.69s) ended 1.36s before
  its planned 7.02s shot, shifting EVERY later shot early so story
  visuals changed before the narrator finished the prior story (user
  report). The render now probes the clip and appends
  `tpad=stop_mode=clone` to hold the last frame to the planned
  duration. qa.py gained a backstop: every rendered shot segment must
  match its planned duration within 0.15s or the run fails.
- Narration voice: Kokoro `am_echo` (user pick from the 9 American male
  voice samples; was `af_sarah`). TTS fingerprint includes the voice,
  so all segments re-synthesize.

## 2026.10.12.1 — 2026-10-12
- Badge pill visibility fix (render.py): the story-number badge's dark pill
  was drawn at alpha-140 black — invisible on black backgrounds, so badges
  rendered as bare numbers. Pill is now a lifted dark gray (48,48,48,235)
  that reads as a pill on black.
- Hook pairs for person-less stories (visuals.py): `_build_hook_pairs`
  now builds a logo-only pair when a story has no person photo (previously
  skipped → hook fell back to a generic article screenshot). Dark logos are
  auto-inverted so they read on black.
- Pipeline versioning introduced: `pipeline/VERSION` + this changelog +
  version stamped into `qa.json`. Upgrade flow documented in the
  `pipeline-upgrade` skill; cron instructions reference it.

## Earlier history
- 2026-10-12: BT.709 colorspace tags on still-image encodes (render.py) —
  fixes green-hue chroma shift on dark backgrounds (user report 00:35).
- 2026-10-12: selfplug.py YuNet face-dedupe (merge overlapping detections).
- 2026-10-12: visuals.py accepts `.png` verified pins (were skipped).
- 2026-10-11: story-number badges #1–#5 (x=W-336, persistent per story),
  headline hook pills (x=w-198), per-letter typewriter captions with
  trailing █, y=960 centering + y=1400 caption-safe clamp, hook
  person+logo pairs in headline hooks (intro reverted to logos-only),
  logo alpha compositing + white-box rejection, dHash no-repeat dedupe,
  screenshot stage (analyze → root-source → crop), no-logo-fullshot rule,
  periods script style (retired comma-heavy), stories ordered smallest
  stakes first.
- 2026-10-11: analytical animations BT.709 tagging (analytics.py).
- 2026-10-09/10: terminal intro + captions, neon green #39FF14, red
  BREAKING kicker, Pixar intro portrait + self-plug emotion montage,
  watermark, H.264 High yuv420p + faststart encode standard.
