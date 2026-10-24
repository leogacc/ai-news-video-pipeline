# Templates

Video templates for this project. Each template is a folder with a
`template.yaml` definition and a `README.md`.

- `daily-digest/` — the main template. The current daily 9:16 video:
  5 stories, hooks, self-plug split montage, deep dives, ~164s.
  Status: live (documented from v2026.10.23.10).
- `clips/` — new template, draft. Single-story short clips, 30-60s,
  same terminal style, one story per clip. Status: draft, unused.

Note: these definitions do not yet drive `pipeline/run.py`. The daily
run still executes from `pipeline/config.yaml` and `pipeline/*.py`.
Wiring a template in as a runtime input (e.g. `run.py --template clips`)
is a separate, approved change — it was not done here, so tonight's
daily run is unaffected.
