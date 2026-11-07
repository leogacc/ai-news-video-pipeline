#!/usr/bin/env python3
"""Deterministic Sound Effects (SFX) Synthesizer (v2026.11.06.12).

Synthesizes high-fidelity, sample-accurate modern tech accents at 48kHz stereo:
- whoosh_subtle.wav (-18 dBFS): Smooth frequency-swept noise burst for cut transitions.
- click_pop.wav (-15 dBFS): Snappy damped sine pop for metric ticks and badge reveals.
- bass_drop.wav (-12 dBFS): Cinematic sub-bass pitch drop for hero reveals.

All SFX are generated 100% locally with zero external dependencies ($0 incremental spend).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict

import numpy as np
import soundfile as sf

SFX_DIR = Path(__file__).resolve().parent / "sfx"
SAMPLE_RATE = 48000


def db_to_linear(db: float) -> float:
    """Converts decibels (dBFS) to linear amplitude multiplier."""
    return 10.0 ** (db / 20.0)


def generate_whoosh_subtle(sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generates a 0.28-second subtle swept noise whoosh (-18 dBFS peak)."""
    duration = 0.28
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # Deterministic pseudo-random noise seeded for perfect reproducibility
    rng = np.random.default_rng(seed=4242)
    white_noise = rng.normal(0, 1.0, (n_samples, 2))

    # Sweeping center frequency band modulation (from 350Hz up to 2400Hz back to 500Hz)
    env = np.sin(np.pi * t / duration) ** 2  # smooth raised cosine envelope
    sweep_freq = 400 + 2000 * np.sin(np.pi * t / duration)

    # Swept tone core blended with shaped noise
    phase = 2 * np.pi * np.cumsum(sweep_freq) / sample_rate
    swept_core = np.sin(phase)[:, np.newaxis]

    # Combine noise and tone with stereo spread
    stereo_spread = np.array([[1.0, 0.85], [0.85, 1.0]])
    audio = 0.65 * (white_noise * env[:, np.newaxis]) + 0.35 * (swept_core * env[:, np.newaxis])
    audio = audio @ stereo_spread

    # Normalize to -18 dBFS peak
    target_peak = db_to_linear(-18.0)
    current_peak = np.max(np.abs(audio))
    if current_peak > 0:
        audio = audio * (target_peak / current_peak)

    return audio.astype(np.float32)


def generate_click_pop(sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generates a 0.06-second snappy modern tech UI click/pop (-15 dBFS peak)."""
    duration = 0.06
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # 1.2 kHz primary frequency with snappy exponential damping
    decay = np.exp(-t / 0.010)
    freq = 1250.0 - 450.0 * (t / duration)  # subtle chirp drop
    signal = np.sin(2 * np.pi * freq * t) * decay

    # Stereo duplicate with subtle 0.5ms channel delay
    delay_samples = int(0.0005 * sample_rate)
    left = signal
    right = np.pad(signal, (delay_samples, 0))[:n_samples]

    audio = np.column_stack([left, right])

    # Normalize to -15 dBFS peak
    target_peak = db_to_linear(-15.0)
    current_peak = np.max(np.abs(audio))
    if current_peak > 0:
        audio = audio * (target_peak / current_peak)

    return audio.astype(np.float32)


def generate_bass_drop(sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generates a 0.60-second deep cinematic sub-bass pitch drop (-12 dBFS peak)."""
    duration = 0.60
    n_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, n_samples, endpoint=False)

    # Frequency sweeps down exponentially from 125 Hz to 42 Hz
    freq = 42.0 + (125.0 - 42.0) * np.exp(-t / 0.18)
    phase = 2 * np.pi * np.cumsum(freq) / sample_rate

    # Fundamental sine wave + subtle 2nd harmonic saturation
    tone = np.sin(phase) + 0.25 * np.sin(2 * phase)

    # Smooth attack (8ms) and exponential decay envelope
    attack_samples = int(0.008 * sample_rate)
    attack = np.linspace(0, 1.0, attack_samples)
    env = np.exp(-t / 0.22)
    env[:attack_samples] *= attack

    audio = tone * env
    # Wide sub-bass stereo
    audio_stereo = np.column_stack([audio, audio])

    # Normalize to -12 dBFS peak
    target_peak = db_to_linear(-12.0)
    current_peak = np.max(np.abs(audio_stereo))
    if current_peak > 0:
        audio_stereo = audio_stereo * (target_peak / current_peak)

    return audio_stereo.astype(np.float32)


def ensure_sfx(output_dir: Path = SFX_DIR) -> Dict[str, Path]:
    """Ensures that all standard SFX audio assets exist on disk.

    Returns:
        Dictionary mapping sfx key to absolute Path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "whoosh": output_dir / "whoosh_subtle.wav",
        "click": output_dir / "click_pop.wav",
        "bass": output_dir / "bass_drop.wav",
    }

    generators = {
        "whoosh": generate_whoosh_subtle,
        "click": generate_click_pop,
        "bass": generate_bass_drop,
    }

    for key, path in paths.items():
        if not path.exists() or path.stat().st_size == 0:
            audio = generators[key]()
            sf.write(str(path), audio, SAMPLE_RATE, subtype="PCM_16")

    return paths


if __name__ == "__main__":
    print(f"Synthesizing SFX into {SFX_DIR}...")
    created = ensure_sfx()
    for name, path in created.items():
        data, sr = sf.read(str(path))
        peak_db = 20 * math.log10(np.max(np.abs(data)))
        duration = len(data) / sr
        print(f"  [{name:7s}] {path.name} | {duration:.2f}s | {sr}Hz | peak: {peak_db:.1f} dBFS")
    print("All SFX successfully synthesized.")
