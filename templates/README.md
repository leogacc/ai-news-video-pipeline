# Templates

Video templates for this project. Each template is a folder with a
`template.yaml` definition and a `README.md`.

- `daily-digest/` — the main template. The current daily 9:16 video:
  5 stories, hooks, self-plug split montage, deep dives, ~164s.
  Status: live (documented from v2026.10.23.10).
- `clips/` — latest template, draft, after the v1–v4 Andreessen test.
  Process a video's transcript, scan it for speaker changes, put the hook
  + same-length bio block in the lower third (face-checked per speaker,
  text moved lower if it hits a face), and use the full video uncut when
  it's information-dense throughout. Full-screen 9:16 face-centred crop.
  Status: draft, unused as code.

## Unified vertical zones (2026-10-25 — all templates)

Every template now carries the same vertical rule, so mid content is
never too high in any format:

- Frame 1080x1920. Captions are FIXED at the bottom (text_top_y 1450,
  first glyph row ~1521+) and never move to accommodate a high stack —
  the stack moves down to the captions.
- Narrated clips: title y135-345, content y375-1325, bio y1370-1500
  (canonical definition: `clips/template.yaml`
  `narrated_clip_zones_1080x1920` + `unified_vertical_zones`).
- All other clip builds: stack/visual bottom within ~25px of the first
  caption glyph row for text stacks, or visual zone filled down to
  y1490 where no bio block intervenes.
- Daily and rumors digests: hook heroes and deep-dive visuals fill
  the frame; padded shots extend their sharp visual to y1490
  (superseding the old y0..1400 cap); self-plug montage window is
  y0..1490. Each template carries its own `vertical_zones` section
  with the measurable check: fail any render whose stack/visual ends
  above y1400 or leaves a >60px gap to the captions, shift it down,
  and re-render.

## Watermark (2026-10-25 — all templates)

Every template now carries the Daily Digest watermark, same spec
everywhere: `@leos.logos`, DejaVuSans-Bold 34pt, white at 50%
opacity, burned on every frame for the whole video. Daily and rumors
put it top-left at x=60, y=190 (rect [60,190,300,228], same row as
the number pills, which sit upper-right). Clips use the same
position for no-face and speaker layouts, and move it up to x=60,
y=80 for narrated clips only, where the title block at y135-345
would collide with y190 — same text, font, size, and opacity, just
above the title box. Previous clips shipped without it; that is now
a defect, checked on start/middle/end stills.

Note: these definitions do not yet drive `pipeline/run.py`. The daily
run still executes from `pipeline/config.yaml` and `pipeline/*.py`.
Wiring a template in as a runtime input (e.g. `run.py --template clips`)
is a separate, approved change — it was not done here, so tonight's
daily run is unaffected. Clip builds, which are built following
`clips/template.yaml` directly (including the scout cron's clips),
use the new zones from the next run.
