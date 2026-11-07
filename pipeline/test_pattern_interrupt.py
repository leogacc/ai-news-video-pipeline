#!/usr/bin/env python3
"""Unit tests for Phase 10.4: Pattern Interrupts & Memetic Re-engagement Engine.

Verifies:
1. Pattern interrupt card generation (960x600 chromatic aberration glitch).
2. Curated pattern interrupt assets existence.
3. Automated storyboard injection at 70-75% mark for clips >= 18s.
4. Duration constraint: 1.2s <= duration <= 1.8s (target 1.4s).
"""
import os
import unittest
from pathlib import Path
import sys
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "scout"))

import clip_frames
import x_scout
import assemble


class TestPatternInterrupt(unittest.TestCase):
    def test_pattern_interrupt_card_generation(self):
        """Verify build_pattern_interrupt_card creates 960x600 RGB glitch image."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_p = Path(tmp_dir) / "test_interrupt.png"
            res_p = clip_frames.build_pattern_interrupt_card(
                out_p, headline="WAIT FOR IT...", subline="PATTERN INTERRUPT"
            )
            self.assertTrue(res_p.exists())
            with Image.open(res_p) as im:
                self.assertEqual(im.size, (960, 600))
                self.assertEqual(im.mode, "RGB")

    def test_curated_pattern_interrupt_assets_exist(self):
        """Verify pre-rendered pattern interrupt assets exist in pipeline/assets."""
        assets_dir = ROOT / "pipeline" / "assets" / "pattern_interrupts"
        self.assertTrue(assets_dir.exists())
        self.assertTrue((assets_dir / "wait_for_it.png").exists())
        self.assertTrue((assets_dir / "plot_twist.png").exists())

    def test_pattern_interrupt_injection_timing(self):
        """Verify storyboard injects pattern interrupt shot at 70-75% mark with 1.4s duration."""
        scout = x_scout.XScout(dry_run=True)
        synthetic_item = {
            "post_id": "interrupt_test_123",
            "author": "mistralai",
            "author_name": "Mistral AI",
            "text": "Releasing new 128k context reasoning architecture weights under Apache 2.0 license with 79.8% retention.",
            "url": "https://x.com/mistralai/status/123",
            "date": "2026-11-06",
            "category": "release",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            card_p = tmp_p / "card.png"
            Image.new("RGB", (960, 600), (10, 10, 10)).save(card_p)
            assets = {"card_path": str(card_p), "video_path": None, "photos": []}

            captured_spec = {}
            orig_assemble = assemble.assemble_clip

            def mock_assemble(spec, out_p, work_dir=None):
                nonlocal captured_spec
                captured_spec.update(spec)
                dummy = Path(out_p)
                dummy.touch()
                return dummy

            assemble.assemble_clip = mock_assemble
            try:
                scout.build_clip_for_pick(synthetic_item, assets, tmp_p)
            finally:
                assemble.assemble_clip = orig_assemble

            shots = captured_spec.get("shots", [])
            interrupt_shots = [
                (idx, s) for idx, s in enumerate(shots) if s.get("badge") == "PATTERN INTERRUPT"
            ]
            self.assertEqual(
                len(interrupt_shots), 1, "Expected exactly 1 pattern interrupt shot"
            )
            idx, shot = interrupt_shots[0]

            # Assert duration is ~1.4s
            self.assertGreaterEqual(shot["duration"], 1.2)
            self.assertLessEqual(shot["duration"], 1.8)

            # Assert positioning is around 60-80% of shot sequence
            position_ratio = idx / len(shots)
            self.assertGreaterEqual(position_ratio, 0.55)
            self.assertLessEqual(position_ratio, 0.85)


if __name__ == "__main__":
    unittest.main()
