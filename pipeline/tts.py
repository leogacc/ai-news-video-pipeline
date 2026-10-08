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


def tighten_pauses(data: np.ndarray, sr: int,
                   thresh_db: float = -35.0,
                   max_pause_sec: float = 0.25,
                   long_sil_sec: float = 0.6) -> np.ndarray:
    """Kokoro leaves 1.2-1.6s dead air after some sentence ends; compress any
    internal silence longer than `long_sil_sec` down to `max_pause_sec` so
    the narration never stalls."""
    if data.size == 0:
        return data
    thresh = 10 ** (thresh_db / 20.0) * max(1e-6, np.abs(data).max())
    silent = np.abs(data) < thresh
    # Find silent runs.
    runs, start, prev = [], 0, silent[0]
    for i, s in enumerate(silent[1:], 1):
        if s != prev:
            runs.append((start, i, prev))
            start, prev = i, s
    runs.append((start, len(silent), prev))
    keep = np.ones(len(data), dtype=bool)
    max_keep = int(max_pause_sec * sr)
    min_sil = int(long_sil_sec * sr)
    edge_keep = int(0.12 * sr)
    for a, b, is_sil in runs:
        if not is_sil or (b - a) <= min_sil:
            continue
        if a == 0:
            # Leading dead air: keep a breath of 0.12s.
            keep[a + edge_keep:b] = False
        elif b == len(data):
            # Trailing dead air: keep 0.12s.
            keep[a:b - edge_keep] = False
        else:
            keep[a + max_keep:b] = False
    out = data[keep]
    return out if out.size else data


def seg_wav(text: str, out: Path):
    from kokoro import KPipeline
    pipeline = KPipeline(lang_code=T["lang_code"])
    chunks = []
    for _, _, audio in pipeline(text, voice=T["voice"], speed=T.get("speed", 1.0)):
        chunks.append(audio)
    wav = torch.cat(chunks, dim=0).numpy()
    wav = tighten_pauses(wav, T["sample_rate"])
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
