#!/usr/bin/env python3
"""Unit tests for Phase 11.3: Dynamic Tension & Metric HUD Widgets.

Verifies:
1. StopwatchTicker.tsx and GrowthPill.tsx exist and register in Root.tsx.
2. animations.SUPPORTED_COMPOSITIONS contains StopwatchTicker and GrowthPill.
3. animations.render_stopwatch_ticker constructs valid props payload.
4. animations.render_growth_pill constructs valid props payload.
"""
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import animations


class TestTensionHUDEngine(unittest.TestCase):
    def test_components_exist_and_registered(self):
        """Verify StopwatchTicker.tsx and GrowthPill.tsx exist and register in Root.tsx."""
        stopwatch_file = ROOT / "pipeline" / "animations" / "src" / "compositions" / "StopwatchTicker.tsx"
        self.assertTrue(stopwatch_file.exists(), "StopwatchTicker.tsx not found")
        sw_content = stopwatch_file.read_text(encoding="utf-8")
        self.assertIn("export const StopwatchTicker", sw_content)
        self.assertIn("targetSeconds", sw_content)

        growth_file = ROOT / "pipeline" / "animations" / "src" / "compositions" / "GrowthPill.tsx"
        self.assertTrue(growth_file.exists(), "GrowthPill.tsx not found")
        gp_content = growth_file.read_text(encoding="utf-8")
        self.assertIn("export const GrowthPill", gp_content)
        self.assertIn("deltaBadge", gp_content)

        root_file = ROOT / "pipeline" / "animations" / "src" / "Root.tsx"
        root_content = root_file.read_text(encoding="utf-8")
        self.assertIn('id="StopwatchTicker"', root_content)
        self.assertIn('id="GrowthPill"', root_content)

    def test_animations_supported_compositions(self):
        """Verify animations.py recognises StopwatchTicker and GrowthPill."""
        self.assertIn("StopwatchTicker", animations.SUPPORTED_COMPOSITIONS)
        self.assertIn("GrowthPill", animations.SUPPORTED_COMPOSITIONS)
        self.assertTrue(hasattr(animations, "render_stopwatch_ticker"))
        self.assertTrue(hasattr(animations, "render_growth_pill"))

    @patch("animations.render_animation")
    def test_render_stopwatch_ticker_props_payload(self, mock_render):
        """Verify render_stopwatch_ticker passes correctly formatted props."""
        mock_render.return_value = Path("/tmp/mock_stopwatch.mp4")

        res = animations.render_stopwatch_ticker(
            target_seconds=9.0,
            output_path="/tmp/mock_stopwatch.mp4",
            label="TIME TO WIPEOUT",
            badge="ESCALATION",
            warning_text="TABLES DROPPED",
            duration_frames=120,
        )

        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        self.assertEqual(kwargs.get("composition") or args[0], "StopwatchTicker")
        props = kwargs.get("props") or args[1]
        self.assertEqual(props["targetSeconds"], 9.0)
        self.assertEqual(props["label"], "TIME TO WIPEOUT")
        self.assertEqual(props["badge"], "ESCALATION")
        self.assertEqual(props["warningText"], "TABLES DROPPED")
        self.assertEqual(kwargs.get("duration_frames") or args[3], 120)

    @patch("animations.render_animation")
    def test_render_growth_pill_props_payload(self, mock_render):
        """Verify render_growth_pill passes correctly formatted props."""
        mock_render.return_value = Path("/tmp/mock_growth.mp4")

        stats = [
            {"label": "LOSS", "value": "$159B"},
            {"label": "TIME", "value": "9s"},
        ]

        res = animations.render_growth_pill(
            value="$159 BILLION",
            output_path="/tmp/mock_growth.mp4",
            trend="down",
            delta_badge="-100%",
            stats=stats,
            duration_frames=90,
        )

        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        self.assertEqual(kwargs.get("composition") or args[0], "GrowthPill")
        props = kwargs.get("props") or args[1]
        self.assertEqual(props["value"], "$159 BILLION")
        self.assertEqual(props["trend"], "down")
        self.assertEqual(props["deltaBadge"], "-100%")
        self.assertEqual(props["stats"], stats)
        self.assertEqual(kwargs.get("duration_frames") or args[3], 90)


if __name__ == "__main__":
    unittest.main()
