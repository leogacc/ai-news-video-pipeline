#!/usr/bin/env python3
"""Unit tests for Clip Assembler (pipeline/assemble.py)."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

import assemble
import clip_frames


class TestAssemble(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_video_overlay_geometry(self):
        """Verify video overlay dimensions, safety limits, and watermark."""
        title_lines = ["NEW REASONING ENGINE", "AUTONOMOUS AGENTS"]
        bio_lines = ["Source: Anthropic Research, 2026"]
        overlay, layout = clip_frames.build_video_overlay(
            title_lines, bio_lines, video_w=1920, video_h=1080
        )

        self.assertEqual(overlay.size, (1080, 1920))
        self.assertEqual(overlay.mode, "RGBA")

        # Geometry bounds
        self.assertGreaterEqual(layout["title"][0], clip_frames.REGION_TOP)
        self.assertLessEqual(layout["bio"][1], clip_frames.CAPTION_FLOOR)
        self.assertEqual(layout["title"][1] + clip_frames.GAP, layout["content_top"])
        self.assertEqual(layout["content_bottom"] + clip_frames.GAP, layout["bio"][0])

    def test_build_terminal_window_overlay(self):
        """Verify terminal window overlay dimensions, mode, and geometry bounds."""
        overlay = clip_frames.build_terminal_window_overlay()
        self.assertEqual(overlay.size, (1080, 1920))
        self.assertEqual(overlay.mode, "RGBA")
        bbox = overlay.getbbox()
        self.assertIsNotNone(bbox)
        # Box centered horizontally at x0=60, x1=1020, and y0=1150, y1=1425
        self.assertEqual(bbox[0], 60)
        self.assertEqual(bbox[1], 1150)
        self.assertEqual(bbox[2], 1020)
        self.assertEqual(bbox[3], 1425)

    def test_generate_karaoke_ass(self):
        """Verify Hybrid Terminal Pop ASS generator outputs valid syntax, safe-zone anchoring, dual-color highlights, and block cursor."""
        words = [
            (0.1, 0.4, "DeepSeek"),
            (0.45, 0.7, "released"),
            (0.75, 1.1, "benchmarks."),
        ]
        ass_path = self.tmp_path / "test.ass"
        assemble.generate_karaoke_ass(words, ass_path)

        self.assertTrue(ass_path.exists())
        content = ass_path.read_text(encoding="utf-8")
        self.assertIn("[Script Info]", content)
        self.assertIn("PlayResX: 1080", content)
        self.assertIn("PlayResY: 1920", content)
        self.assertIn("Style: Terminal", content)
        self.assertIn("1205", content)  # MarginV safe-zone top-anchoring inside terminal box
        self.assertIn("█", content)  # Neon green terminal block cursor
        self.assertIn(",1,2,0,7,", content)  # BorderStyle=1 with Outline=2 and Alignment=7
        self.assertIn("Dialogue:", content)
        self.assertIn("&H0000E6FF", content)  # Electric Cyber Yellow
        self.assertIn("{\\c&H0000E6FF&}", content)  # Active word highlight tag
        self.assertIn("{\\c&H0014FF39&}", content)  # Secondary neon green restoration tag


    def test_assemble_multi_shot_clip(self):
        """Synthesize a complete multi-shot clip (still + Remotion ladder) with TTS and captions."""
        # Create a test still image
        sample_img = self.tmp_path / "sample_chart.png"
        img = Image.new("RGB", (960, 540), (20, 24, 28))
        img.save(str(sample_img))

        spec = {
            "title_lines": ["REASONING LEAP", "BENCHMARK RESULTS"],
            "bio_lines": ["Source: Research Paper, 2026"],
            "script": [
                "A new open reasoning model just demonstrated frontier performance on math and coding.",
                "The system establishes state of the art results while running on standard hardware.",
            ],
            "shots": [
                {
                    "type": "still",
                    "src": str(sample_img),
                    "duration": 2.0,
                },
                {
                    "type": "animation",
                    "composition": "BenchmarkLadder",
                    "props": {
                        "title": "CODING BENCHMARK",
                        "benchmarkName": "HumanEval",
                        "items": [
                            {"label": "New Model", "value": 92.4, "highlight": True, "badge": "SOTA"},
                            {"label": "Baseline A", "value": 81.0, "baseline": True},
                            {"label": "Baseline B", "value": 74.5, "baseline": True},
                        ],
                        "deltaCallout": "+11.4% LEAP",
                    },
                    "duration": 2.5,
                },
            ],
        }

        out_mp4 = self.tmp_path / "test_clip.mp4"
        final_path = assemble.assemble_clip(spec, out_mp4, work_dir=self.tmp_path / "work")

        self.assertEqual(final_path, out_mp4)
        self.assertTrue(out_mp4.exists())
        self.assertGreater(out_mp4.stat().st_size, 50_000)

        # Probe final video with ffprobe
        meta = assemble.probe_video(out_mp4)
        self.assertEqual(meta["width"], 1080)
        self.assertEqual(meta["height"], 1920)
        self.assertEqual(meta["codec"], "h264")
        self.assertGreaterEqual(meta["duration"], 4.0)

        # Check that verification stills were generated
        stills_dir = self.tmp_path / "stills"
        self.assertTrue(stills_dir.exists())
        self.assertTrue((stills_dir / "still_10pct.png").exists())
        self.assertTrue((stills_dir / "still_50pct.png").exists())
        self.assertTrue((stills_dir / "still_90pct.png").exists())

    def test_assemble_tweet_card_3d_shot(self):
        """Verify assembling a clip with auto-promoted TweetCard3D shot."""
        card_png = self.tmp_path / "tweet_card_sample.png"
        img = Image.new("RGB", (900, 600), (15, 23, 42))
        img.save(str(card_png))

        spec = {
            "title_lines": ["BREAKING X DISPATCH"],
            "bio_lines": ["Source: Official Announcement, 2026"],
            "script": [
                "Researchers released an official announcement demonstrating breakthrough results.",
            ],
            "shots": [
                {
                    "type": "tweet_card",
                    "src": str(card_png),
                    "duration": 2.5,
                    "title": "OFFICIAL COMMUNITY RELEASE",
                    "badge": "VERIFIED",
                },
            ],
            "enable_sfx": True,
        }

        out_mp4 = self.tmp_path / "tweet_3d_clip.mp4"
        final_path = assemble.assemble_clip(spec, out_mp4, work_dir=self.tmp_path / "work_tweet")

        self.assertEqual(final_path, out_mp4)
        self.assertTrue(out_mp4.exists())
        meta = assemble.probe_video(out_mp4)
        self.assertEqual(meta["width"], 1080)
        self.assertEqual(meta["height"], 1920)


if __name__ == "__main__":
    unittest.main()
