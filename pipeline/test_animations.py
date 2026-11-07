#!/usr/bin/env python3
"""Unit tests for Remotion Animation Engine (pipeline/animations.py)."""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

import animations


def _probe_video(video_path: Path) -> dict:
    """Helper to probe video stream metadata using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,codec_name,duration",
        "-of",
        "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    assert "streams" in data and len(data["streams"]) > 0, "No video stream found"
    return data["streams"][0]


class TestAnimations(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_supported_compositions_set(self):
        self.assertIn("BenchmarkLadder", animations.SUPPORTED_COMPOSITIONS)
        self.assertIn("ArchitectureDiagram", animations.SUPPORTED_COMPOSITIONS)
        self.assertIn("KineticMetricCounter", animations.SUPPORTED_COMPOSITIONS)
        self.assertIn("TweetCard3D", animations.SUPPORTED_COMPOSITIONS)

    def test_invalid_composition_raises_value_error(self):
        out_file = self.tmp_path / "invalid.mp4"
        with self.assertRaises(ValueError):
            animations.render_animation(
                composition="FakeComposition",
                props={},
                output_path=out_file,
            )

    def test_render_benchmark_ladder(self):
        out_file = self.tmp_path / "ladder_test.mp4"
        items = [
            {"label": "o3-mini (High)", "value": 89.2, "highlight": True, "badge": "NEW SOTA"},
            {"label": "Claude 3.5 Sonnet", "value": 78.4, "baseline": True},
            {"label": "GPT-4o", "value": 72.1, "baseline": True},
        ]

        rendered_path = animations.render_benchmark_ladder(
            title="REASONING BENCHMARK BREAKTHROUGH",
            benchmark_name="SWE-bench Verified",
            items=items,
            output_path=out_file,
            subtitle="Autonomous software engineering problem resolution",
            delta_callout="+10.8% OVER CLAUDE",
            duration_frames=30,  # 1.0 second fast render for test
        )

        self.assertEqual(rendered_path, out_file)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 50_000)

        meta = _probe_video(out_file)
        self.assertEqual(meta["width"], 1080)
        self.assertEqual(meta["height"], 1920)
        self.assertEqual(meta["codec_name"], "h264")
        self.assertEqual(meta["r_frame_rate"], "30/1")

    def test_render_architecture_diagram(self):
        out_file = self.tmp_path / "diagram_test.mp4"
        nodes = [
            {"id": "n1", "step": "01", "title": "Orchestrator", "subtitle": "Decomposes input prompt", "badge": "INPUT"},
            {"id": "n2", "step": "02", "title": "Reasoning Core", "subtitle": "Chain-of-thought search", "badge": "REASONING"},
            {"id": "n3", "step": "03", "title": "Tool Worker", "subtitle": "Executes shell sandbox actions", "badge": "EXECUTION"},
        ]

        rendered_path = animations.render_architecture_diagram(
            title="AGENT WORKFLOW ARCHITECTURE",
            nodes=nodes,
            output_path=out_file,
            subtitle="Multi-agent parallel execution pipeline",
            category="SYSTEM DESIGN",
            duration_frames=30,  # 1.0 second fast render for test
        )

        self.assertEqual(rendered_path, out_file)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 50_000)

        meta = _probe_video(out_file)
        self.assertEqual(meta["width"], 1080)
        self.assertEqual(meta["height"], 1920)
        self.assertEqual(meta["codec_name"], "h264")
        self.assertEqual(meta["r_frame_rate"], "30/1")

    def test_render_kinetic_counter(self):
        out_file = self.tmp_path / "counter_test.mp4"
        sub_metrics = [
            {"label": "Throughput", "value": "240 tok/s", "change": "+4.1x"},
            {"label": "VRAM", "value": "12 GB", "change": "-50%"},
        ]

        rendered_path = animations.render_kinetic_counter(
            title="INFERENCE SPEED MILESTONE",
            target_value=240.0,
            output_path=out_file,
            subtitle="FlashAttention-3 kernel optimization",
            badge="HARDWARE TELEMETRY",
            metric_label="GENERATION SPEED",
            suffix=" tok/s",
            decimals=0,
            delta_callout="4.1X SPEEDUP",
            sub_metrics=sub_metrics,
            duration_frames=30,  # 1.0 second fast render for test
        )

        self.assertEqual(rendered_path, out_file)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 50_000)

        meta = _probe_video(out_file)
        self.assertEqual(meta["width"], 1080)
        self.assertEqual(meta["height"], 1920)
        self.assertEqual(meta["codec_name"], "h264")
        self.assertEqual(meta["r_frame_rate"], "30/1")

    def test_render_cli_props_file(self):
        """Test invoking render.mjs directly with a JSON spec file."""
        spec_file = self.tmp_path / "spec.json"
        out_file = self.tmp_path / "cli_ladder.mp4"
        spec_data = {
            "title": "CLI SPEC TEST",
            "benchmarkName": "HumanEval",
            "items": [
                {"label": "Model A", "value": 90.0, "highlight": True},
                {"label": "Model B", "value": 75.0, "baseline": True},
            ],
        }
        spec_file.write_text(json.dumps(spec_data))

        render_mjs = Path(animations.__file__).resolve().parent / "animations" / "render.mjs"
        node_bin = shutil.which("node") or "/usr/local/bin/node"

        cmd = [
            node_bin,
            str(render_mjs),
            "--composition",
            "BenchmarkLadder",
            "--props",
            str(spec_file),
            "--out",
            str(out_file),
            "--durationInFrames",
            "30",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"CLI render failed: {res.stderr}\n{res.stdout}")
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 50_000)

    def test_render_tweet_card_3d(self):
        """Test rendering TweetCard3D Remotion composition."""
        from PIL import Image, ImageDraw

        card_png = self.tmp_path / "card.png"
        im = Image.new("RGB", (800, 500), color=(15, 23, 42))
        d = ImageDraw.Draw(im)
        d.text((40, 40), "Sample Tweet Content", fill=(255, 255, 255))
        im.save(card_png)

        out_file = self.tmp_path / "tweet_3d_test.mp4"
        rendered = animations.render_tweet_card_3d(
            card_image_path=card_png,
            output_path=out_file,
            title="VERIFIED RESEARCH BREAKTHROUGH",
            subtitle="Autonomous AI Engineering",
            badge="OFFICIAL DISPATCH",
            duration_frames=30,
        )

        self.assertEqual(rendered, out_file)
        self.assertTrue(out_file.exists())
        self.assertGreater(out_file.stat().st_size, 50_000)

        meta = _probe_video(out_file)
        self.assertEqual(meta["width"], 1080)
        self.assertEqual(meta["height"], 1920)
        self.assertEqual(meta["codec_name"], "h264")
        self.assertEqual(meta["r_frame_rate"], "30/1")


if __name__ == "__main__":
    unittest.main()
