#!/usr/bin/env python3
"""PRODUCER (captions) — faster-whisper word timestamps -> phrase-card .ass.

Reference style (@theventure): NOT karaoke. Text swaps phrase-by-phrase
every ~2-3s — faster than the visual cuts. ALL-CAPS bold, black text on a
white opaque box, bottom third (Alignment 2). Punch-phrase pills are drawn
separately by render.py (white on black, mid-frame).
80%+ of social video is watched muted — captions are the retention
mechanism, not decoration.
"""
import json
import re
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

    # Group into phrase cards: break at sentence end, or when a card would
    # exceed ~2.8s / 12 words. Cards swap faster than the visual cuts.
    phrases, cur = [], []
    for s, e, w in words:
        cur.append((s, e, w))
        ends = bool(re.search(r"[.?!:;]$", w))
        if ends or len(cur) >= 12 or (cur and e - cur[0][0] > 2.8):
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)

    # ALL-CAPS, black text on white opaque box (BorderStyle=3), bottom third.
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Phrase,Arial,62,&H00000000,&H00000000,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,10,0,2,60,60,110,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    # Whisper mishears product names the TTS voice pronounces fine.
    # Fix them on the caption cards (uppercase space).
    FIXUPS = [
        ("SPACEX'S AI", "SPACEXSI"),
        ("SPACE X S I", "SPACEXSI"),
        ("SPACEX AI", "SPACEXSI"),
        ("TSAR", "CZAR"),
        ("NAME'S", "NAMES"),
    ]
    for ph in phrases:
        start, end = ph[0][0], ph[-1][1]
        body = " ".join(w for _, _, w in ph).upper()
        for bad, good in FIXUPS:
            body = body.replace(bad, good)
        body = body.replace("{", "\\{").replace("}", "\\}")
        events.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},Phrase,,0,0,0,,{body}")

    out = ROOT / "output" / "captions.ass"
    out.write_text(header + "\n".join(events) + "\n")
    # Word timestamps for per-sentence shot timing in visuals.py.
    (ROOT / "output" / "words.json").write_text(json.dumps(
        [{"start": round(s, 3), "end": round(e, 3), "word": w}
         for s, e, w in words], indent=1))
    print(f"[captions] {len(words)} words -> {len(phrases)} cards -> {out}")


if __name__ == "__main__":
    main()
