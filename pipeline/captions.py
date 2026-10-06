#!/usr/bin/env python3
"""PRODUCER (captions) — faster-whisper word timestamps -> karaoke .ass.

CapCut-style: active word highlighted, rest white, middle-third placement
(Alignment 5) so platform UI never covers the text. 80%+ of social video is
watched muted — captions are the retention mechanism, not decoration.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
C = CFG["captions"]


def ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main():
    from faster_whisper import WhisperModel
    model = WhisperModel(C["whisper_model"], device="cpu", compute_type="int8")
    wav = str(ROOT / "output" / "narration_full.wav")
    segments, _ = model.transcribe(wav, word_timestamps=True, language="en")

    words = []
    for seg in segments:
        for w in (seg.words or []):
            words.append((w.start, w.end, w.word.strip()))
    words = [(s, e, w) for s, e, w in words if w]
    if not words:
        raise RuntimeError("[captions] whisper returned no words")

    # Group into short lines for 9:16.
    lines, cur = [], []
    for s, e, w in words:
        cur.append((s, e, w))
        if len(cur) >= C["max_words_per_line"] or (cur and e - cur[0][0] > 3.5):
            lines.append(cur)
            cur = []
    if cur:
        lines.append(cur)

    # NOTE on karaoke colors: in ASS, {\kf} sweeps the fill from SecondaryColour
    # (unsung) to PrimaryColour (sung). If your render shows the highlight
    # inverted (unsung words yellow), swap PrimaryColour and SecondaryColour below.
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Arial,76,&H0000CCFF,&H00FFFFFF,&H90000000,&H90000000,-1,0,0,0,100,100,0,0,1,5,1,5,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for line in lines:
        start, end = line[0][0], line[-1][1]
        body = "".join(
            "{\\kf%d}%s " % (max(1, int(round((e - s) * 100))), w)
            for s, e, w in line).strip()
        events.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},Karaoke,,0,0,0,,{body}")

    out = ROOT / "output" / "captions.ass"
    out.write_text(header + "\n".join(events) + "\n")
    print(f"[captions] {len(words)} words -> {len(lines)} lines -> {out}")


if __name__ == "__main__":
    main()
