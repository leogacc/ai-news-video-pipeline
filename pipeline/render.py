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
    # Ken Burns speed by segment kind: the hook punches in fast, headlines
    # drift at medium speed, story breakdowns get a slow settle. Clips
    # already move, so they never get artificial motion.
    ZOOM_RATE = {"hook": 0.0028, "headlines": 0.0016, "story": 0.0009}
    for v in visuals:
        i, dur = v["segment"], v["duration"]
        out = seg_dir / f"seg_{i:02d}.mp4"
        if v["kind"] == "clip":
            vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},fps={fps},setsar=1")
            run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", v["path"],
                 "-t", f"{dur:.2f}", "-vf", vf, "-an",
                 "-c:v", "libx264", "-preset", preset, "-crf", "23",
                 str(out)])
        else:  # photo / title card -> Ken Burns zoom, speed by segment kind
            frames = max(1, int(dur * fps))
            rate = ZOOM_RATE.get(v.get("seg_kind", "story"), 0.0009)
            zoom = random.choice(["in", "out"])
            # 'on' = output frame count; zoompan always starts at zoom=1,
            # so zoom-out is expressed as a decreasing function of 'on'.
            z = (f"min(1+{rate}*on,1.18)" if zoom == "in"
                 else f"max(1.18-{rate}*on,1.0)")
            vf = (f"scale={w*2}:-2,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
                  f"y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps={fps},setsar=1")
            run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(fps),
                 "-t", f"{dur:.2f}", "-i", v["path"],
                 "-vf", vf, "-frames:v", str(frames), "-an",
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
    run(["ffmpeg", "-y", *inputs,
         "-filter_complex", afilter,
         "-vf", f"ass={captions}",
         "-map", "0:v", "-map", amap,
         "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
         "-r", str(fps), "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
         "-shortest", "-movflags", "+faststart", str(final)])
    print(f"[render] done -> {final}")


if __name__ == "__main__":
    main()
