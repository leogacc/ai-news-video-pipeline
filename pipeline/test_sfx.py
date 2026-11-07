#!/usr/bin/env python3
"""Unit tests for Phase 7 SFX Engine (pipeline/test_sfx.py)."""

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

from pipeline.assets.generate_sfx import (
    SAMPLE_RATE,
    ensure_sfx,
    generate_whoosh_subtle,
    generate_click_pop,
    generate_bass_drop,
)
from pipeline.assemble import generate_sfx_track, ClipAssembler


class TestSFXEngine(unittest.TestCase):
    """Verifies audio synthesis, loudness calibration, and track generation."""

    def test_sfx_generators(self):
        """Verify standalone generator functions produce calibrated audio."""
        whoosh = generate_whoosh_subtle(SAMPLE_RATE)
        self.assertEqual(whoosh.shape[1], 2, "Whoosh must be stereo")
        self.assertAlmostEqual(len(whoosh) / SAMPLE_RATE, 0.28, delta=0.01)
        whoosh_peak = 20 * math.log10(np.max(np.abs(whoosh)))
        self.assertAlmostEqual(whoosh_peak, -18.0, delta=0.5)

        click = generate_click_pop(SAMPLE_RATE)
        self.assertEqual(click.shape[1], 2, "Click must be stereo")
        self.assertAlmostEqual(len(click) / SAMPLE_RATE, 0.06, delta=0.01)
        click_peak = 20 * math.log10(np.max(np.abs(click)))
        self.assertAlmostEqual(click_peak, -15.0, delta=0.5)

        bass = generate_bass_drop(SAMPLE_RATE)
        self.assertEqual(bass.shape[1], 2, "Bass drop must be stereo")
        self.assertAlmostEqual(len(bass) / SAMPLE_RATE, 0.60, delta=0.01)
        bass_peak = 20 * math.log10(np.max(np.abs(bass)))
        self.assertAlmostEqual(bass_peak, -12.0, delta=0.5)

    def test_ensure_sfx_files(self):
        """Verify ensure_sfx() outputs valid WAV files."""
        sfx_dict = ensure_sfx()
        self.assertIn("whoosh", sfx_dict)
        self.assertIn("click", sfx_dict)
        self.assertIn("bass", sfx_dict)

        for key, path in sfx_dict.items():
            self.assertTrue(path.exists(), f"SFX file {path} should exist")
            data, sr = sf.read(str(path))
            self.assertEqual(sr, SAMPLE_RATE)
            self.assertEqual(data.ndim, 2, f"{key} should have 2 channels")
            self.assertGreater(len(data), 0)

    def test_generate_sfx_track(self):
        """Verify timeline placement and track multiplexing."""
        durations = [2.5, 3.5, 2.0]
        shots = [
            {"type": "still"},
            {"type": "remotion"},
            {"type": "tweet_card"},
        ]
        total_dur = sum(durations) + 0.5

        with tempfile.TemporaryDirectory() as td:
            out_sfx = Path(td) / "test_sfx.wav"
            res = generate_sfx_track(durations, shots, total_dur, out_sfx)

            self.assertTrue(res.exists())
            data, sr = sf.read(str(res))
            self.assertEqual(sr, SAMPLE_RATE)
            self.assertEqual(data.ndim, 2)
            self.assertAlmostEqual(len(data) / sr, total_dur, delta=0.02)

            # Confirm audio is non-silent and within safe limits
            peak = np.max(np.abs(data))
            self.assertGreater(peak, 0.02, "Track should contain SFX events")
            self.assertLessEqual(peak, 0.98, "Track must not digitally clip")

    def test_clip_assembler_sfx_flag(self):
        """Verify ClipAssembler honors enable_sfx configuration."""
        spec_with_sfx = {"enable_sfx": True, "shots": []}
        spec_no_sfx = {"enable_sfx": False, "shots": []}

        ca1 = ClipAssembler(spec_with_sfx)
        self.assertTrue(ca1.enable_sfx)

        ca2 = ClipAssembler(spec_no_sfx)
        self.assertFalse(ca2.enable_sfx)


if __name__ == "__main__":
    unittest.main()
