#!/usr/bin/env python3
"""PRODUCER (render) — two-pass ffmpeg.

Pass 1: each segment -> 1080x1920 (or 1280x720) clip. Clips are center-cropped;
stills (photos, title cards) get a Ken Burns zoom whose speed follows the
segment kind: hook punches in fast, headlines drift, stories settle slow.
Pass 2: concat -> burn karaoke captions -> mix narration + ducked music bed ->
loudnorm -> H.264 MP4 with faststart.

Two passes instead of one giant filtergraph: far easier to debug on a weak VM,
and a failed segment doesn't nuke a 40-minute encode.
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())


def run(cmd):
    print("[render]", " ".join(cmd[:6]), "...")
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    w, h, fps = CFG[mode]["width"], CFG[mode]["height"], CFG[mode]["fps"]
    preset, crf = CFG[mode]["preset"], CFG[mode]["crf"]

    visuals = json.loads((ROOT / "output" / "visuals.json").read_text())
    seg_dir = ROOT / "output" / "segments"
    seg_dir.mkdir(exist_ok=True)

    seg_files = []
    # Ken Burns speed by segment kind: quick, subtle zooms that read inside
    # 4-6s shots. The pace comes from hard cuts, the zoom just adds life.
    ZOOM_RATE = {"hook": 0.0028, "headlines": 0.0022, "story": 0.0018}
    for v in visuals:
        i, dur = v["idx"], v["duration"]
        out = seg_dir / f"shot_{i:02d}.mp4"
        logo = v.get("logo")
        # Logo overlay: company identifier composited top-right over the
        # base scene (rule 7: company + action -> layer them).
        def with_logo(base_vf, main_args):
            lvf = (f"{base_vf}[base];"
                   f"[1:v]scale=220:-1:flags=lanczos,format=rgba[lg];"
                   f"[base][lg]overlay=W-w-40:40")
            return (["ffmpeg", "-y"] + main_args +
                    ["-loop", "1", "-i", logo,
                     "-t", f"{dur:.2f}", "-filter_complex", lvf])
        if v["kind"] == "clip":
            vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},fps={fps},setsar=1")
            base = ["-stream_loop", "-1", "-i", v["path"]]
            cmd = (with_logo(f"[0:v]{vf}", base) if logo else
                   ["ffmpeg", "-y"] + base +
                   ["-t", f"{dur:.2f}", "-vf", vf])
            run(cmd + ["-an", "-c:v", "libx264", "-preset", preset,
                       "-crf", "23", str(out)])
        else:  # photo / title card -> Ken Burns zoom, speed by segment kind
            frames = max(1, int(dur * fps))
            rate = ZOOM_RATE.get(v.get("seg_kind", "story"), 0.0009)
            zoom = random.choice(["in", "out"])
            # 'on' = output frame count; zoompan always starts at zoom=1,
            # so zoom-out is expressed as a decreasing function of 'on'.
            z = (f"min(1+{rate}*on,1.18)" if zoom == "in"
                 else f"max(1.18-{rate}*on,1.0)")
            # Center-crop to 9:16 BEFORE zoompan: zoompan stretches its zoom
            # window to the output size, so wide photos came out squeezed.
            vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
                  f"crop={w*2}:{h*2},"
                  f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
                  f"y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps={fps},setsar=1")
            base = ["-loop", "1", "-framerate", str(fps), "-i", v["path"]]
            cmd = (with_logo(f"[0:v]{vf}", base) if logo else
                   ["ffmpeg", "-y"] + base + ["-vf", vf])
            run(cmd + ["-t", f"{dur:.2f}", "-frames:v", str(frames), "-an",
                       "-c:v", "libx264", "-preset", preset, "-crf", "23",
                       str(out)])
        seg_files.append(out)

    lst = ROOT / "output" / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in seg_files))
    vcat = ROOT / "output" / "video_concat.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(vcat)])

    narration = ROOT / "output" / "narration_full.wav"
    captions = ROOT / "output" / "captions.ass"
    music_dir = ROOT / "assets" / "music"
    tracks = sorted(music_dir.glob("*.mp3")) if music_dir.exists() else []
    music = random.choice(tracks) if tracks else None

    inputs = ["-i", str(vcat), "-i", str(narration)]
    if music:
        inputs += ["-i", str(music)]
        # music bed at low constant volume under the voiceover, then loudnorm
        # the whole mix to broadcast-ish levels.
        afilter = ("[2:a]volume=0.12,aloop=loop=-1:size=2147483647[bg];"
                   "[1:a][bg]amix=inputs=2:duration=first:dropout_transition=0,"
                   "loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
        amap = "[aout]"
    else:
        afilter = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        amap = "[aout]"

    final = ROOT / "output" / f"ainews_{mode}.mp4"
    # Emphasis pills: 2-4 word punch labels, white bold text on a black box,
    # centered mid-frame (never fights the bottom-third caption cards).
    vf_parts = [f"ass={captions}"]
    # Never cut the speaker: frame rounding can leave the shot plan a hair
    # shorter than the narration. Pad the video out to the narration length
    # instead of letting -shortest truncate the audio.
    vdur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(vcat)],
        capture_output=True, text=True).stdout.strip() or 0)
    ndur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(narration)],
        capture_output=True, text=True).stdout.strip() or 0)
    pad = max(0.0, ndur - vdur)
    if pad > 0.02:
        vf_parts.append(f"tpad=stop_mode=clone:stop_duration={pad:.3f}")
        print(f"[render] padding video {pad:.2f}s to narration length")
    script = json.loads((ROOT / "output" / "script.json").read_text())
    # Emphasis pills as ASS events (not drawtext): they fade in right before
    # the emphasized words are spoken, and sit away from faces.
    words = json.loads((ROOT / "output" / "words.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())

    def _norm(w):
        return re.sub(r"[^a-z0-9]", "", w.lower())

    def _ts(sec):
        sec = max(0.0, sec)
        h_, rem = divmod(sec, 3600)
        m_, s_ = divmod(rem, 60)
        return f"{int(h_)}:{int(m_):02d}:{s_:05.2f}"

    def find_phrase(seg_words, phrase):
        """(start, end) of the emphasis phrase in the whisper word stream."""
        want = [_norm(w) for w in phrase.split()]
        want = [w_ for w_ in want if w_]
        if not want or not seg_words:
            return None
        have = [_norm(w_["word"]) for w_ in seg_words]
        for s_ in range(len(have)):
            if have[s_] != want[0]:
                continue
            h_, wi = s_, 0
            while h_ < len(have) and wi < len(want):
                if have[h_] == want[wi]:
                    wi += 1
                h_ += 1
            if wi == len(want):
                return seg_words[s_]["start"], seg_words[h_ - 1]["end"]
        return None

    emph_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Emphasis,Arial,76,&H00FFFFFF,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,8,0,5,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    emph_events = []
    for si, seg in enumerate(script["segments"]):
        emph = (seg.get("emphasis") or "").strip()
        if not emph or si >= len(timings):
            continue
        tm = timings[si]
        seg_start, seg_end = tm["start"], tm["start"] + tm["duration"]
        seg_words = [w_ for w_ in words
                     if w_["start"] >= seg_start - 0.05 and w_["start"] < seg_end]
        m = find_phrase(seg_words, emph)
        if m:
            w0, w1 = m
            estart, eend = max(seg_start, w0 - 0.35), min(seg_end, w1 + 0.8)
        else:
            estart, eend = seg_start + 0.3, seg_end
        # Face-aware position: person shots center the face, so the pill
        # goes to the upper area; otherwise mid-frame.
        face_shot = any(
            v.get("person") and not (v["start"] + v["duration"] <= estart
                                    or v["start"] >= eend)
            for v in visuals if v["segment"] == si)
        y = int(h * 0.22) if face_shot else int(h * 0.42)
        safe = emph.replace("{", "\\{").replace("}", "\\}")
        emph_events.append(
            f"Dialogue: 0,{_ts(estart)},{_ts(eend)},Emphasis,,0,0,0,,"
            f"{{\\fad(300,250)\\pos(540,{y})}}{safe}")
    if emph_events:
        epath = ROOT / "output" / "emphasis.ass"
        epath.write_text(emph_header + "\n".join(emph_events) + "\n")
        vf_parts.append(f"ass={epath}")
        print(f"[render] {len(emph_events)} emphasis pills (timed + face-aware)")
    run(["ffmpeg", "-y", *inputs,
         "-filter_complex", afilter,
         "-vf", ",".join(vf_parts),
         "-map", "0:v", "-map", amap,
         "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
         "-r", str(fps), "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
         "-shortest", "-movflags", "+faststart", str(final)])
    print(f"[render] done -> {final}")


if __name__ == "__main__":
    main()
