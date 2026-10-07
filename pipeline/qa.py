#!/usr/bin/env python3
"""QA GATE (blocking) — any failure aborts the run and alerts. Nothing partial
ever publishes."""
import json
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
        words_cap = ass.read_text().count("\\kf")
        check("caption coverage", words_cap >= 0.8 * words_spoken,
              f"({words_cap}/{words_spoken} words)")

    # The high-school requirement, enforced in code.
    from textstat import flesch_kincaid_grade
    script = json.loads((ROOT / "output" / "script.json").read_text())
    full_text = " ".join(s["text"] for s in script["segments"])
    grade = flesch_kincaid_grade(full_text)
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
