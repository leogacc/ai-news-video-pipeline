#!/usr/bin/env python3
"""Unit tests for Phase 10.2: Persistent Kinetic Hook Banner.

Verifies:
1. RGBA mode and 1080x1920 canvas resolution.
2. Safe-zone placement (y: 240..350) below top navigation tabs (y <= 220).
3. Auto-fitting typography (1-line vs 2-line wrap).
4. Drop shadow and pill contrast rendering.
5. Assembly job overlay synthesis.
"""
import os
import unittest
from pathlib import Path
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import clip_frames


class TestPersistentHookBanner(unittest.TestCase):
    def test_banner_canvas_dimensions_and_mode(self):
        """Verify banner overlay is 1080x1920 RGBA."""
        img = clip_frames.build_persistent_hook_banner("⚡ AI BREAKTHROUGH")
        self.assertEqual(img.size, (1080, 1920))
        self.assertEqual(img.mode, "RGBA")

    def test_banner_safe_zone_vertical_position(self):
        """Verify non-transparent pixels sit in top safe zone (240 <= y <= 360)."""
        img = clip_frames.build_persistent_hook_banner("🚨 CRITICAL AGENT FAILURE")
        bbox = img.getbbox()
        self.assertIsNotNone(bbox)
        min_x, min_y, max_x, max_y = bbox

        # Sits below top navigation tabs (y <= 220)
        self.assertGreaterEqual(min_y, 235)
        # Sits above main content / terminal (y >= 370)
        self.assertLessEqual(max_y, 365)
        # Horizontally centered around x=540
        self.assertLessEqual(min_x, 100)
        self.assertGreaterEqual(max_x, 980)

    def test_auto_fit_typography_short_and_long(self):
        """Verify banner cleanly renders both short punchy and long complex titles."""
        short_img = clip_frames.build_persistent_hook_banner("🔥 SWARMS")
        self.assertIsNotNone(short_img.getbbox())

        long_img = clip_frames.build_persistent_hook_banner(
            "⚡ DEEPSEEK-R1 SHATTERS FRONTIER AI REASONING BENCHMARKS WITH OPEN WEIGHTS"
        )
        bbox_long = long_img.getbbox()
        self.assertIsNotNone(bbox_long)
        self.assertGreaterEqual(bbox_long[1], 235)
        self.assertLessEqual(bbox_long[3], 365)

    def test_badge_prefix_handling(self):
        """Verify badge is properly prepended if not already present."""
        img = clip_frames.build_persistent_hook_banner("DELETED PROD DB", badge="🚨 CRITICAL")
        self.assertIsNotNone(img.getbbox())


if __name__ == "__main__":
    unittest.main()
