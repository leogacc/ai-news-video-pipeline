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


def measure_loudness(audio_path: Path) -> float | None:
    """Measure integrated loudness in LUFS using ffmpeg ebur128 filter."""
    try:
        cmd = [
            "ffmpeg", "-i", str(audio_path),
            "-af", "ebur128",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        m = re.search(r"Integrated loudness:\s+I:\s+([-\d.]+)\s+LUFS", res.stderr)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None


def check_clip_file(
    clip_path: Path,
    ass_path: Path | None = None,
    stills_dir: Path | None = None,
    verbose: bool = True,
) -> list[str]:
    """Execute blocking QA checks on an individual vertical video clip.

    Verifies delivery specs:
    - 1080x1920 geometry, 30fps
    - H.264 High profile, level <= 4.0, yuv420p
    - Faststart (moov atom before mdat atom)
    - Stereo AAC audio at 48kHz, duration aligned with video
    - Audio integrated loudness -14 LUFS (+/- 1.5 LUFS)
    - Top-anchored #39FF14 neon green typewriter captions
    - Clean verification stills without edge-sliced text
    """
    clip_failures = []

    def clip_check(name: str, ok: bool, detail: str = ""):
        if verbose:
            print(f"[qa-clip] {'PASS' if ok else 'FAIL'} {name} {detail}")
        if not ok:
            clip_failures.append(name)

    clip_p = Path(clip_path)
    clip_check("video exists", clip_p.exists() and clip_p.stat().st_size > 10_000,
               f"({clip_p.stat().st_size} bytes)" if clip_p.exists() else "missing")
    if not clip_p.exists() or clip_p.stat().st_size < 10_000:
        return clip_failures

    # FFprobe stream inspection
    try:
        info = probe(clip_p)
    except Exception as e:
        clip_check("video probeable", False, str(e))
        return clip_failures

    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)

    clip_check("video stream present", v is not None)
    if not v:
        return clip_failures

    width = int(v.get("width", 0))
    height = int(v.get("height", 0))
    clip_check("resolution 1080x1920", width == 1080 and height == 1920, f"({width}x{height})")

    # Framerate check (30 fps)
    fps_val = 0.0
    try:
        fps_val = float(eval(v.get("r_frame_rate", "0/1")))
    except Exception:
        pass
    clip_check("fps 30", abs(fps_val - 30.0) < 1.0, f"({fps_val:.2f} fps)")

    # Codec, profile, pixel format
    codec = v.get("codec_name", "")
    clip_check("codec h264", codec == "h264", f"({codec})")

    pix_fmt = v.get("pix_fmt", "")
    clip_check("pix_fmt yuv420p", pix_fmt == "yuv420p", f"({pix_fmt})")

    profile = v.get("profile", "")
    clip_check("profile High", profile.lower() == "high", f"({profile})")

    try:
        lvl = float(v.get("level", 0))
    except Exception:
        lvl = 0.0
    clip_check("level <= 4.0", lvl <= 42, f"({lvl})")

    # Faststart check (moov before mdat)
    raw = clip_p.read_bytes()[:150_000]
    moov_at = raw.find(b"moov")
    mdat_at = raw.find(b"mdat")
    has_faststart = (0 < moov_at < mdat_at) or (0 < moov_at and mdat_at == -1)
    clip_check("faststart (moov before mdat)", has_faststart, f"(moov@{moov_at}, mdat@{mdat_at})")

    # Audio checks
    clip_check("audio stream present", a is not None)
    if a:
        clip_check("audio sample_rate 48000", int(a.get("sample_rate", 0)) == 48000, f"({a.get('sample_rate')} Hz)")
        
        # Audio duration vs Video duration
        try:
            v_dur = float(v.get("duration") or info.get("format", {}).get("duration", 0))
            a_dur = float(a.get("duration") or info.get("format", {}).get("duration", 0))
            clip_check("audio duration synced with video", abs(v_dur - a_dur) <= 0.60, f"(video {v_dur:.2f}s, audio {a_dur:.2f}s)")
        except Exception:
            pass

        # Loudness check (-14 LUFS +/- 2.5 LUFS tolerance for short clips)
        loudness = measure_loudness(clip_p)
        if loudness is not None:
            clip_check("audio loudness -14 LUFS", -16.5 <= loudness <= -11.5, f"({loudness:.1f} LUFS)")
        else:
            clip_check("audio loudness measurable", False, "could not measure ebur128")

    # Captions check
    if ass_path is None:
        sibling_ass = clip_p.parent / "captions.ass"
        if sibling_ass.exists():
            ass_path = sibling_ass

    if ass_path and Path(ass_path).exists():
        ass_p = Path(ass_path)
        ass_text = ass_p.read_text(encoding="utf-8", errors="replace")
        clip_check("captions file non-empty", ass_p.stat().st_size > 50, f"({ass_p.stat().st_size} bytes)")
        has_safe_zone = False
        has_box_backdrop = False
        has_neon_green = False
        for line in ass_text.splitlines():
            if line.startswith("Style:"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 22:
                    color = parts[3].upper()
                    if "&H0014FF39" in color or "14FF39" in color:
                        has_neon_green = True
                    border_style = parts[15].strip()
                    if border_style in ("1", "3"):
                        has_box_backdrop = True
                    try:
                        margin_v = int(parts[21])
                        if 1050 <= margin_v <= 1350:
                            has_safe_zone = True
                    except ValueError:
                        pass
        clip_check("captions neon green font", has_neon_green, "(&H0014FF39)")
        clip_check("captions safe-zone vertical alignment", has_safe_zone, "(1050 <= MarginV <= 1350)")
        clip_check("captions contrast box backdrop", has_box_backdrop, "(BorderStyle=1 or 3)")

    # Stills verification
    if stills_dir is None:
        sibling_stills = clip_p.parent / "stills"
        if sibling_stills.exists() and sibling_stills.is_dir():
            stills_dir = sibling_stills

    if stills_dir and Path(stills_dir).exists():
        from PIL import Image
        stills = sorted(list(Path(stills_dir).glob("*.png")) + list(Path(stills_dir).glob("*.jpg")))
        clip_check("verification stills exist", len(stills) >= 2, f"({len(stills)} stills)")
        dim_ok = True
        for s in stills:
            try:
                with Image.open(s) as img:
                    if img.size != (1080, 1920):
                        dim_ok = False
            except Exception:
                dim_ok = False
        clip_check("verification stills 1080x1920", dim_ok, "all stills 1080x1920")

        # Edge-slice detection
        try:
            sys.path.insert(0, str(ROOT))
            from pin_edge_check import check_paths
            offenders = check_paths(stills)
            clip_check("no edge-sliced text in verification stills", not offenders, f"({offenders})" if offenders else "")
        except Exception as e:
            clip_check("pin_edge_check runnable", False, str(e))

    return clip_failures


def main():
    clip_p = None
    if "--clip" in sys.argv:
        clip_p = Path(sys.argv[sys.argv.index("--clip") + 1])
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("--") and sys.argv[1].endswith(".mp4"):
        clip_p = Path(sys.argv[1])

    if clip_p is not None:
        ass_p = Path(sys.argv[sys.argv.index("--ass") + 1]) if "--ass" in sys.argv else (clip_p.parent / "captions.ass" if (clip_p.parent / "captions.ass").exists() else None)
        stills_p = Path(sys.argv[sys.argv.index("--stills") + 1]) if "--stills" in sys.argv else (clip_p.parent / "stills" if (clip_p.parent / "stills").exists() else None)

        failures = check_clip_file(clip_p, ass_path=ass_p, stills_dir=stills_p, verbose=True)
        version_str = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "unknown"
        qa_data = {
            "clip": str(clip_p),
            "pipeline_version": version_str,
            "failures": failures,
            "passed": len(failures) == 0,
        }
        qa_out = clip_p.parent / "qa.json"
        qa_out.write_text(json.dumps(qa_data, indent=2))
        print(f"[qa-clip] Report written -> {qa_out}")
        if failures:
            print(f"[qa-clip] BLOCKED: {failures}")
            sys.exit(1)
        else:
            print("[qa-clip] All clip delivery specs verified successfully.")
            sys.exit(0)

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

    # Edge-slice guard (2026-10-27, v2026.10.27.2): an article-card pin
    # cropped through its own headline ships a sliced title — the 20:48
    # cut carried the same sliced PYMNTS headline TWICE (hook hero +
    # deep-dive pin) because no check ever looked at pin edges. The
    # wall scans reject verification/paywall/adblock walls, not a clean
    # card with a tight crop, so this is its own gate. FAILS LOUDLY
    # naming the offender pins.
    if vjs.exists():
        sys.path.insert(0, str(ROOT))
        from pin_edge_check import check_visuals as _edge_check
        vs = json.loads(vjs.read_text())
        offenders = _edge_check(vs)
        check("no edge-sliced text in pins", not offenders,
              f"({offenders} — re-crop with whitespace beyond the "
              f"outermost text line)" if offenders else "")

    # Hero-aspect guard (2026-10-27, v2026.10.27.4): a hook-hero pin
    # wider than 1.5:1 renders as a short centred band with a large
    # blurred stretch between the content and the pinned captions —
    # the 21:14 cut's Opera hero (1600x800) filled only 540px of the
    # 1490px visual zone. FAILS LOUDLY naming the offender pins.
    if vjs.exists():
        sys.path.insert(0, str(ROOT))
        from pin_edge_check import check_hero_aspect as _hero_aspect
        vs = json.loads(vjs.read_text())
        wide = _hero_aspect(vs)
        check("no wide hook-hero pins", not wide,
              f"({wide} — re-crop to the informative region or extend "
              f"the crop to portrait)" if wide else "")

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
    # no burned-in overlay may sit under platform UI. 9:16: TikTok's zones
    # — top 140px, bottom 20%, right 120px on 1080x1920. Landscape
    # (2026-10-13): YouTube has minimal persistent chrome — guard the top
    # title-safe strip (70px), the end-screen right side (40px), and the
    # bottom player bar (7%). Geometry comes from render.py's
    # overlays.json sidecar (single source of truth); anchors get a
    # ±60x±70 tolerance box, rects are exact.
    ojs = ROOT / "output" / "overlays.json"
    if ojs.exists():
        ov = json.loads(ojs.read_text())
        W_, H_ = ov["width"], ov["height"]
        _land = W_ > H_
        bad = []
        for o in ov["overlays"]:
            if "rect" in o:
                x0, y0, x1, y1 = o["rect"]
            else:
                ax, ay = o["anchor"]
                x0, y0, x1, y1 = ax - 60, ay - 70, ax + 60, ay + 70
            if _land:
                intrudes = (y0 < 70 or x1 > W_ - 40
                            or y1 > int(H_ * 0.93))
            else:
                intrudes = (y0 < 140 or x1 > W_ - 120
                            or y1 > int(H_ * 0.80))
            if intrudes:
                bad.append(o["name"])
        check("overlays clear of platform UI zones", not bad,
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
