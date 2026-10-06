#!/usr/bin/env python3
"""PRODUCER (audio) — Kokoro TTS per segment -> narration_full.wav + timings.json.

Fixed voice (config) = channel identity. ~1x real-time on 2 vCPUs; a 60s
voiceover takes roughly a minute.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
T = CFG["tts"]


def seg_wav(text: str, out: Path):
    from kokoro import KPipeline
    pipeline = KPipeline(lang_code=T["lang_code"])
    chunks = []
    for _, _, audio in pipeline(text, voice=T["voice"]):
        chunks.append(audio)
    wav = torch.cat(chunks, dim=0).numpy()
    sf.write(str(out), wav, T["sample_rate"])


def wav_duration(p: Path) -> float:
    return sf.info(str(p)).duration


def main():
    script = json.loads((ROOT / "output" / "script.json").read_text())
    segs = script["segments"]
    audio_dir = ROOT / "output" / "audio"
    audio_dir.mkdir(exist_ok=True)

    timings, parts = [], []
    sr = T["sample_rate"]
    gap = int(T["segment_gap_sec"] * sr)
    full = []
    t = 0.0
    for i, seg in enumerate(segs):
        p = audio_dir / f"seg_{i:02d}.wav"
        seg_wav(seg["text"], p)
        dur = wav_duration(p)
        data, _ = sf.read(str(p))
        full.append(data)
        full.append(np.zeros(gap, dtype=data.dtype))
        timings.append({"segment": i, "start": round(t, 3), "duration": round(dur, 3)})
        t += dur + T["segment_gap_sec"]
        print(f"[tts] seg {i}: {dur:.1f}s")

    narration = np.concatenate(full)
    out_wav = ROOT / "output" / "narration_full.wav"
    sf.write(str(out_wav), narration, sr)
    (ROOT / "output" / "timings.json").write_text(json.dumps(timings, indent=2))
    print(f"[tts] narration_full.wav ({len(narration)/sr:.1f}s)")


if __name__ == "__main__":
    main()
