#!/usr/bin/env python3
"""QA GATE (blocking) — any failure aborts the run and alerts. Nothing partial
ever publishes."""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
Q = CFG["qa"]

failures = []


def check(name: str, ok: bool, detail: str = ""):
    print(f"[qa] {'PASS' if ok else 'FAIL'} {name} {detail}")
    if not ok:
        failures.append(name)


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    video = ROOT / "output" / f"ainews_{mode}.mp4"
    check("video exists", video.exists() and video.stat().st_size > 500_000,
          f"({video.stat().st_size/1e6:.1f} MB)" if video.exists() else "")

    if video.exists():
        info = probe(video)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
        check("resolution", int(v["width"]) == CFG[mode]["width"]
              and int(v["height"]) == CFG[mode]["height"],
              f"({v['width']}x{v['height']})")
        check("fps", abs(float(eval(v["r_frame_rate"])) - CFG[mode]["fps"]) < 1,
              f"({v['r_frame_rate']})")
        check("has audio", a is not None)

        vdur = float(info["format"]["duration"])
        timings = json.loads((ROOT / "output" / "timings.json").read_text())
        expected = sum(t["duration"] for t in timings) + \
            CFG["tts"]["segment_gap_sec"] * len(timings)
        check("duration sane", abs(vdur - expected) <= Q["duration_tolerance_sec"],
              f"(video {vdur:.1f}s vs narration {expected:.1f}s)")

    ass = ROOT / "output" / "captions.ass"
    check("captions exist", ass.exists() and ass.stat().st_size > 200)
    if ass.exists():
        words_spoken = sum(len(s["text"].split()) for s in
                           json.loads((ROOT / "output" / "script.json").read_text())["segments"])
        # Phrase-card captions: count words across Dialogue texts.
        words_cap = 0
        for ln in ass.read_text().splitlines():
            if ln.startswith("Dialogue:"):
                parts = ln.split(",", 9)
                if len(parts) == 10:
                    words_cap += len(parts[9].strip().split())
        check("caption coverage", words_cap >= 0.8 * words_spoken,
              f"({words_cap}/{words_spoken} words)")

    # Visual variety (2026-10-09): two adjacent shots must never show the
    # identical file — a frozen frame reads as a stalled video. (The clip
    # library already avoids handing the same clip to adjacent shots;
    # this is the backstop.)
    vjs = ROOT / "output" / "visuals.json"
    if vjs.exists():
        vs = json.loads(vjs.read_text())
        dupes = [(a["idx"], b["idx"]) for a, b in zip(vs, vs[1:])
                 if a["path"] == b["path"]]
        check("no consecutive duplicate visuals", not dupes,
              f"(shots {dupes})" if dupes else "")

    # Black-frame guard (user standing rule, 2026-10-11): a black frame is
    # a FAILED shot and must never ship — fail the run instead.
    if vjs.exists():
        vs = json.loads(vjs.read_text())
        black = [s["idx"] for s in vs
                 if s.get("source") in ("black-frame", "duplicate-needs-review")
                 or Path(s.get("path", "")).name.startswith("black_")]
        check("no black-frame shots", not black,
              f"(shots {black} — pin a real visual)" if black else "")

    # Shot timing sanity (2026-10-09): shots must be chronological and
    # non-overlapping — a match_shot regression once collapsed two shots
    # onto the same start and silently de-synced the visuals.
    if vjs.exists():
        vs = json.loads(vjs.read_text())
        bad = [a["idx"] for a, b in zip(vs, vs[1:])
               if b["start"] < a["start"] + a["duration"] - 0.05]
        check("shots chronological/non-overlapping", not bad,
              f"(shots {bad})" if bad else "")

    # Shot-duration guard (2026-10-12): every rendered shot segment must
    # match its planned duration. A no-loop clip shorter than its shot
    # (self-plug 5.69s vs 7.02s planned) used to end early, shifting every
    # later shot early — story visuals changed before the narrator
    # finished the prior story. render.py now holds the last frame; this
    # is the backstop.
    if vjs.exists():
        vs = json.loads(vjs.read_text())
        bad = []
        for s in vs:
            p = ROOT / "output" / "segments" / f"shot_{s['idx']:02d}.mp4"
            if not p.exists():
                continue
            try:
                actual = float(probe(p)["format"]["duration"])
            except Exception:
                continue
            if abs(actual - s["duration"]) > 0.15:
                bad.append(s["idx"])
        check("shot durations match plan", not bad,
              f"(shots {bad} off by >0.15s)" if bad else "")

    # Delivery spec (video-delivery-specs, 2026-10-11): TikTok wants H.264,
    # yuv420p, High profile, level <= 4.0, faststart (moov before mdat).
    if video.exists():
        info = probe(video)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        check("codec h264", v["codec_name"] == "h264")
        check("pix_fmt yuv420p", v["pix_fmt"] == "yuv420p")
        check("profile high", v.get("profile") == "High")
        check("level <= 4.0", float(v.get("level", 0)) <= 40,
              f"(level {v.get('level')})")
        raw = video.read_bytes()
        moov_at, mdat_at = raw.find(b"moov"), raw.find(b"mdat")
        check("faststart (moov before mdat)",
              0 < moov_at < mdat_at, f"(moov@{moov_at}, mdat@{mdat_at})")

    # Safe-area guard (short-form-video/shot-composition, 2026-10-11):
    # no burned-in overlay may sit under TikTok's UI — top 140px, bottom
    # 20%, right 120px on 1080x1920. Geometry comes from render.py's
    # overlays.json sidecar (single source of truth); anchors get a
    # ±60x±70 tolerance box, rects are exact.
    ojs = ROOT / "output" / "overlays.json"
    if ojs.exists():
        ov = json.loads(ojs.read_text())
        W_, H_ = ov["width"], ov["height"]
        bad = []
        for o in ov["overlays"]:
            if "rect" in o:
                x0, y0, x1, y1 = o["rect"]
            else:
                ax, ay = o["anchor"]
                x0, y0, x1, y1 = ax - 60, ay - 70, ax + 60, ay + 70
            if y0 < 140 or x1 > W_ - 120 or y1 > int(H_ * 0.80):
                bad.append(o["name"])
        check("overlays clear of TikTok UI zones", not bad,
              f"({bad} intrude)" if bad else "")

    # The high-school requirement, enforced in code.
    from textstat import flesch_kincaid_grade
    script = json.loads((ROOT / "output" / "script.json").read_text())
    full_text = " ".join(s["text"] for s in script["segments"])
    # Pacing style is comma-heavy (periods -> commas for 1x TTS flow).
    # Restore sentence boundaries before grading, or the metric explodes.
    grade_text = re.sub(r",\s+", ". ", full_text)
    grade = flesch_kincaid_grade(grade_text)
    check("reading level <= 9.5", grade <= Q["max_grade_level"],
          f"(grade {grade:.1f})")

    if failures:
        print(f"[qa] BLOCKED: {failures}")
    else:
        print("[qa] all checks passed")
    (ROOT / "output" / "qa.json").write_text(json.dumps({"failures": failures}))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
