#!/usr/bin/env python3
"""Unit tests for Phase 11.2: Interactive Live CLI & Code Execution Simulator.

Verifies:
1. TerminalRunner Remotion component exists and registers in Root.tsx.
2. animations.SUPPORTED_COMPOSITIONS contains TerminalRunner.
3. animations.render_terminal_runner constructs valid props payload.
4. TerminalRunner handles typing duration, stdout lines, and refusal badges.
"""
import os
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import animations


class TestTerminalRunnerEngine(unittest.TestCase):
    def test_terminal_runner_files_exist(self):
        """Verify TerminalRunner.tsx exists and is registered in Root.tsx."""
        comp_file = ROOT / "pipeline" / "animations" / "src" / "compositions" / "TerminalRunner.tsx"
        self.assertTrue(comp_file.exists(), "TerminalRunner.tsx not found")
        content = comp_file.read_text(encoding="utf-8")
        self.assertIn("export const TerminalRunner", content)
        self.assertIn("refusalBadge", content)
        self.assertIn("typingDurationFrames", content)

        root_file = ROOT / "pipeline" / "animations" / "src" / "Root.tsx"
        root_content = root_file.read_text(encoding="utf-8")
        self.assertIn('id="TerminalRunner"', root_content)
        self.assertIn("TerminalRunnerProps", root_content)

    def test_animations_supported_compositions(self):
        """Verify animations.py recognises TerminalRunner composition."""
        self.assertIn("TerminalRunner", animations.SUPPORTED_COMPOSITIONS)
        self.assertTrue(hasattr(animations, "render_terminal_runner"))

    @patch("animations.render_animation")
    def test_render_terminal_runner_props_payload(self, mock_render):
        """Verify render_terminal_runner passes correctly formatted props."""
        mock_render.return_value = Path("/tmp/mock_terminal.mp4")

        stdout = [
            {"text": "[INIT] Connecting to DB...", "type": "info"},
            {"text": "[BLOCK] Command refused", "type": "error"},
        ]

        res = animations.render_terminal_runner(
            command="$ noorm db:drop --prod",
            output_path="/tmp/mock_terminal.mp4",
            typing_duration_frames=35,
            stdout_lines=stdout,
            refusal_badge="REFUSED: DROP TABLE BLOCKED",
            is_refusal=True,
            badge="LIVE CLI SIMULATION",
            duration_frames=120,
        )

        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        self.assertEqual(kwargs.get("composition") or args[0], "TerminalRunner")
        props = kwargs.get("props") or args[1]
        self.assertEqual(props["command"], "$ noorm db:drop --prod")
        self.assertEqual(props["typingDurationFrames"], 35)
        self.assertEqual(props["stdoutLines"], stdout)
        self.assertEqual(props["refusalBadge"], "REFUSED: DROP TABLE BLOCKED")
        self.assertTrue(props["isRefusal"])
        self.assertEqual(kwargs.get("duration_frames") or args[3], 120)


if __name__ == "__main__":
    unittest.main()
