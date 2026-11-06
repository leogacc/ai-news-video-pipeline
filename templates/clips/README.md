# Clips

Latest template, after the v1–v4 Andreessen test (2026-10-24). A clip is
processed from a video, not written from scratch:

1. **Process the transcript from a video** — reuse the pipeline video's
   script / word timings if it has them, otherwise transcribe it with
   faster-whisper (base.en) with word timings.
2. **Scan the transcript for who is talking when** — label every segment
   with a speaker (diarization where available, otherwise verified
   turn-taking), and record every speaker-change timestamp.
3. **Title + bio in the lower third, away from the face** — the hook,
   with enough context to name what it's about, plus a separate bio block
   (name, role, show/context) directly under it. The bio block is the
   SAME length as the title block, measured, not eyeballed.
4. **Check the text against every speaker's face** — frame-check at each
   speaker segment's start and midpoint. If the text hits the active
   speaker's face, move the text stack a little lower and re-check, keeping
   it above any burnt-in subtitles. Re-centre the full-screen 9:16 crop on
   the active speaker, so the main person talking stays centred.
5. **Don't cut a dense video** — if the whole source is information-dense
   and relevant to the hook throughout, use it full, uncut. Only trim to a
   single contiguous part when the rest is clearly filler, and then start
   at the definition and end on a complete thought, never mid-anecdote.

No new terminal captions when the source already has burnt-in subtitles.

Every clip also carries the Daily Digest watermark `@leos.logos`
(DejaVuSans-Bold 34pt, white at 50%, every frame) — top-left at
x=60, y=190, or x=60, y=80 for narrated clips, where the title block
would collide with y190. See `template.yaml` `style.watermark`.

See `template.yaml` for the full definition: input, the 10 processing
steps, format, title/bio layout, crop, and publish format.

Status: draft, nothing uses this template yet as code. No pipeline code
change was made with this update, and no run or schedule was created.
The v1–v4 test renders were hand-built following this template's rules,
not by a wired `run.py --template clips` path.
