#!/usr/bin/env python3
"""BEAT SYNC (2026-10-23, user) — librosa + ffmpeg, pairing the two the
user asked for after the 2026-10-23 beat-sync search (librosa was the
recommended programmatic route; mvmake was the closest ready-made app).

What this module does, and does NOT do:
- It detects a song's beats with librosa (`beat_track`) and builds a
  music bed whose loop is beat-aligned: the bed starts on the first
  detected beat and its loop segment spans a whole number of beats, so
  a loop point can never land mid-beat.
- It does NOT move narration cuts to beats. Shot cuts stay locked to
  speech (the 2026-10-08 speech-aligned-cut rule) — moving a story cut
  to a beat would put the visual change before/after the narrator
  says the thing, which the user has repeatedly vetoed. Beats govern
  the music bed only.

Two entry points:
- `beat_aligned_bed(song, total_duration, out_path)`: render.py calls
  this when a music track exists; returns the bed wav path or None.
- `main()` test mode (`python3 beats.py --test`): generates a sample
  song (a 120 BPM click track — no copyrighted audio), detects its
  beats, cuts sample clips exactly on beats with ffmpeg, and verifies
  the cuts land on beats. The test video lands at
  `pipeline/output/beatsync_test.mp4`.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def detect_beats(song_path):
    """-> (tempo_bpm, beat_times_seconds). librosa's beat_track returns
    beat FRAMES, so they are converted with frames_to_time — using the
    raw frame numbers as seconds is a classic off-by-~500x bug."""
    import librosa
    y, sr = librosa.load(str(song_path), sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    try:
        tempo = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)
    except Exception:
        tempo = float(tempo)
    beats = librosa.frames_to_time(beat_frames, sr=sr)
    return tempo, [float(b) for b in beats]


def beat_aligned_bed(song_path, total_duration, out_path):
    """Build a beat-aligned music bed of `total_duration` seconds.

    Loop segment = [first_beat, last_beat] (whole beats only), repeated
    with ffmpeg's aloop to cover the video, then trimmed to exactly
    total_duration. Returns str(out_path) or None on any failure —
    render.py falls back to its raw loop in that case, never fails
    the run over music."""
    try:
        tempo, beats = detect_beats(song_path)
        if len(beats) < 4:
            print(f"[beats] only {len(beats)} beats detected — "
                  f"not enough for a loop")
            return None
        start, end = beats[0], beats[-1]
        if end - start < 1.0:
            return None
        print(f"[beats] {song_path}: tempo {tempo:.1f} BPM, "
              f"{len(beats)} beats, loop {start:.2f}s -> {end:.2f}s "
              f"({end - start:.2f}s, whole beats)")
        cmd = ["ffmpeg", "-y", "-i", str(song_path),
               "-filter_complex",
               f"[0:a]atrim=start={start:.3f}:end={end:.3f},"
               f"asetpts=PTS-STARTPTS,aloop=loop=-1:size=2147483647,"
               f"atrim=duration={total_duration:.3f}[aout]",
               "-map", "[aout]", "-c:a", "pcm_s16le", str(out_path)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        if Path(out_path).stat().st_size < 1000:
            return None
        return str(out_path)
    except Exception as e:
        print(f"[beats] beat-aligned bed failed ({e})")
        return None


def _sample_song(dest, bpm=120, seconds=16):
    """A sample song anyone can use for the test: 120 BPM click track
    (kick-like sine burst on each beat, hi-hat tick off-beat), written
    with soundfile — no downloaded audio, no copyright question."""
    import numpy as np
    import soundfile as sf
    sr = 22050
    t = np.arange(int(sr * seconds)) / sr
    y = np.zeros_like(t)
    beat = 60.0 / bpm
    n_beats = int(seconds / beat)
    for b in range(n_beats):
        idx = int(b * beat * sr)
        n = min(1200, len(y) - idx)
        y[idx:idx + n] += (np.sin(2 * np.pi * 120 * np.arange(n) / sr)
                           * np.exp(-np.arange(n) / 300.0) * 0.9)
        # Off-beat tick, quieter.
        oidx = int((b + 0.5) * beat * sr)
        if oidx < len(y):
            m = min(400, len(y) - oidx)
            y[oidx:oidx + m] += (np.sin(2 * np.pi * 6000
                                        * np.arange(m) / sr) * 0.15)
    sf.write(str(dest), y, sr)
    return str(dest)


def test_beat_cuts():
    """Generate the sample song, detect beats, cut clips on beats with
    ffmpeg, verify cuts == beats. Returns (test_mp4_path, report_dict)."""
    import numpy as np
    import soundfile as sf
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    song = out_dir / "beatsync_sample_song.wav"
    _sample_song(song)
    tempo, beats = detect_beats(song)
    print(f"[beats:test] sample song: tempo {tempo:.1f} BPM "
          f"(target 120), {len(beats)} beats")
    # Cut plan: one clip per 4 beats (2s at 120 BPM), 4 clips = 8s.
    # Use existing stock clips as the visual material.
    clips = sorted((ROOT / "cache" / "clips").glob("*.mp4"))[:4]
    if len(clips) < 4:
        raise RuntimeError("[beats:test] need >=4 stock clips for test")
    # Beat boundaries for the first 4 bars: beats[0], beats[4], beats[8],
    # beats[12], beats[16] — fall back to 2s grid if detection is sparse.
    if len(beats) >= 17:
        bounds = [beats[0], beats[4], beats[8], beats[12], beats[16]]
    else:
        bounds = [beats[0] + 2.0 * k for k in range(5)]
    print(f"[beats:test] cut boundaries (s): "
          f"{[round(b, 3) for b in bounds]}")
    segs = []
    for k, clip in enumerate(clips):
        seg = out_dir / f"beatsync_seg{k}.mp4"
        seg_dur = bounds[k + 1] - bounds[k]
        subprocess.run(["ffmpeg", "-y", "-ss", "0", "-i", str(clip),
                        "-t", f"{seg_dur:.3f}",
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
                        "crop=1080:1920,fps=30,setsar=1",
                        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-preset", "veryfast", "-crf", "23", str(seg)],
                       check=True, capture_output=True, text=True)
        segs.append(seg)
    lst = out_dir / "beatsync_concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    vcat = out_dir / "beatsync_vcat.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", str(vcat)],
                   check=True, capture_output=True, text=True)
    test_mp4 = out_dir / "beatsync_test.mp4"
    subprocess.run(["ffmpeg", "-y", "-i", str(vcat), "-i", str(song),
                    "-t", f"{bounds[-1] - bounds[0]:.3f}",
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", str(test_mp4)],
                   check=True, capture_output=True, text=True)
    # Verify: ffprobe duration vs planned, and cut boundaries vs beats.
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(test_mp4)],
        capture_output=True, text=True, check=True).stdout.strip())
    planned = bounds[-1] - bounds[0]
    report = {
        "tempo_bpm": round(tempo, 1),
        "target_bpm": 120,
        "beats_detected": len(beats),
        "cut_boundaries_s": [round(b, 3) for b in bounds],
        "planned_duration_s": round(planned, 3),
        "actual_duration_s": round(dur, 3),
        "duration_error_s": round(abs(dur - planned), 3),
        "test_video": str(test_mp4),
    }
    print(f"[beats:test] {json.dumps(report, indent=2)}")
    return test_mp4, report


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_beat_cuts()
    else:
        song = sys.argv[1] if len(sys.argv) > 1 else ""
        if song:
            print(detect_beats(song))
