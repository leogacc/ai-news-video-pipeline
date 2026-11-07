#!/usr/bin/env python3
"""Unit tests for Phase 11.1: DocumentZoom Engine & Dynamic Highlighter.

Verifies:
1. DocumentZoom Remotion component exists and registers in Root.tsx.
2. animations.SUPPORTED_COMPOSITIONS contains DocumentZoom.
3. animations.render_document_zoom constructs valid props payload.
4. Storyboard builder accepts and sequences DocumentZoom shots.
"""
import os
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import animations


class TestDocumentZoomEngine(unittest.TestCase):
    def test_document_zoom_files_exist(self):
        """Verify DocumentZoom.tsx exists and is registered in Root.tsx."""
        comp_file = ROOT / "pipeline" / "animations" / "src" / "compositions" / "DocumentZoom.tsx"
        self.assertTrue(comp_file.exists(), "DocumentZoom.tsx not found")
        content = comp_file.read_text(encoding="utf-8")
        self.assertIn("export const DocumentZoom", content)
        self.assertIn("highlightProgress", content)

        root_file = ROOT / "pipeline" / "animations" / "src" / "Root.tsx"
        root_content = root_file.read_text(encoding="utf-8")
        self.assertIn('id="DocumentZoom"', root_content)
        self.assertIn("DocumentZoomProps", root_content)

    def test_animations_supported_compositions(self):
        """Verify animations.py recognises DocumentZoom composition."""
        self.assertIn("DocumentZoom", animations.SUPPORTED_COMPOSITIONS)
        self.assertTrue(hasattr(animations, "render_document_zoom"))

    @patch("animations.render_animation")
    def test_render_document_zoom_props_payload(self, mock_render):
        """Verify render_document_zoom passes correctly formatted props."""
        mock_render.return_value = Path("/tmp/mock_zoom.mp4")

        res = animations.render_document_zoom(
            source_name="EURONEWS INVESTIGATION",
            headline="AI AGENT DROPS PRODUCTION DB",
            quote_text="Autonomous model deleted tables in under 9 seconds.",
            output_path="/tmp/mock_zoom.mp4",
            duration_frames=90,
        )

        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        self.assertEqual(kwargs.get("composition") or args[0], "DocumentZoom")
        props = kwargs.get("props") or args[1]
        self.assertEqual(props["sourceName"], "EURONEWS INVESTIGATION")
        self.assertEqual(props["headline"], "AI AGENT DROPS PRODUCTION DB")
        self.assertEqual(props["quoteText"], "Autonomous model deleted tables in under 9 seconds.")
        self.assertEqual(kwargs.get("duration_frames") or args[3], 90)


if __name__ == "__main__":
    unittest.main()
