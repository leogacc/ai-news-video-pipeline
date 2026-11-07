"""Unit tests for the automated Cloud Cron scout orchestrator (Objective 3.2).

Tests:
1. TikTok description formatting (5 hashtags, no AI self-identification, verified source link).
2. Silent exit contract on runs where candidates do not clear the gate.
3. End-to-end clip assembly on a synthetic top pick.
4. Record keeping in clipped_finds and state.
5. CLI execution of x_scout.py --run-cron --dry-run.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scout"))
sys.path.insert(0, str(ROOT / "pipeline"))

import x_scout
import assemble


class TestCronRunner(unittest.TestCase):
    def setUp(self):
        self.scout = x_scout.XScout(dry_run=True)

    def test_format_tiktok_description(self):
        """Verify TikTok description has 5 hashtags, hook title, question, and no AI claims."""
        item = {
            "post_id": "1899999999999999999",
            "author": "karpathy",
            "author_name": "Andrej Karpathy",
            "text": "Built a clean YouTube client HackerTube in 2 hours to filter 43M comments with Claude 3.7. Code is open on github.com/karpathy/hackertube",
            "url": "https://x.com/karpathy/status/1899999999999999999",
            "date": "2026-11-06",
        }
        desc_data = self.scout.format_tiktok_description(item)
        self.assertIn("title", desc_data)
        self.assertIn("description", desc_data)
        self.assertIn("hashtags", desc_data)

        # 1. Exactly 5 hashtags
        self.assertEqual(len(desc_data["hashtags"]), 5)
        for tag in desc_data["hashtags"]:
            self.assertTrue(tag.startswith("#"))

        # 2. Description formatting
        desc = desc_data["description"]
        self.assertIn("Source: https://x.com/karpathy/status/1899999999999999999", desc)
        self.assertIn("Andrej Karpathy", desc)
        self.assertIn("?", desc)  # Must include engagement question

        # 3. Never claim to be AI
        self.assertNotIn("As an AI", desc)
        self.assertNotIn("I am an AI", desc)
        self.assertNotIn("As a language model", desc)

    def test_silent_exit_on_below_bar_candidates(self):
        """When candidates fail the scorecard, run_cron must exit silently and return None."""
        below_bar_candidates = [
            {
                "post_id": "plugin_1",
                "author": "test_dev",
                "text": "ChatGPT adds support for iCloud Mail plugin integration.",
                "url": "https://x.com/test_dev/status/plugin_1",
                "has_media": False,
                "likes": 50,
            },
            {
                "post_id": "meme_1",
                "author": "hype_man",
                "text": "lol lmao crazy vibes on the timeline today ratio",
                "url": "https://x.com/hype_man/status/meme_1",
                "has_media": False,
                "likes": 200,
            },
        ]
        with patch.object(self.scout, "scan_vip_accounts", return_value=below_bar_candidates):
            with patch.object(self.scout, "scan_keyword_queries", return_value=[]):
                with patch.object(self.scout, "persist_new_items", return_value=None):
                    result = self.scout.run_cron(limit_per_account=2, limit_per_query=2)
                    self.assertIsNone(result)

    def test_record_clipped_find(self):
        """Verify record_clipped_find records metadata in clipped_finds and state."""
        item = {
            "post_id": "test_clip_record_123",
            "author": "deepseek_ai",
            "text": "DeepSeek-R1 technical report published",
            "url": "https://x.com/deepseek_ai/status/test_clip_record_123",
            "excitement_scores": {"total": 36, "hook": 9, "educational": 10, "stakes": 9, "visual": 8},
        }
        clip_p = ROOT / "pipeline" / "output" / "scout" / "clips" / "test_folder" / "clip.mp4"

        # Test dry-run preserves state
        orig_len = len(self.scout.clipped_finds)
        self.scout.record_clipped_find(item, clip_p)
        self.assertEqual(len(self.scout.clipped_finds), orig_len)

        # Test non dry-run writes
        scout_live = x_scout.XScout(dry_run=False)
        with patch("x_scout.atomic_save_json") as mock_save:
            scout_live.record_clipped_find(item, clip_p)
            self.assertTrue(mock_save.called)
            self.assertIn("test_clip_record_123", scout_live.state["posted_find_ids"])
            self.assertEqual(scout_live.clipped_finds[-1]["post_id"], "test_clip_record_123")

    def test_build_clip_for_pick_synthetic(self):
        """Verify building a clip from a synthetic top pick produces a valid clip.mp4."""
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            card_img = tmp_path / "tweet_card_test.png"
            Image.new("RGB", (960, 600), color=(20, 20, 20)).save(card_img)

            synthetic_item = {
                "post_id": "1899999999999999999",
                "author": "karpathy",
                "author_name": "Andrej Karpathy",
                "text": "Built a clean YouTube client HackerTube in 2 hours to filter 43M comments. SOTA reasoning benchmarks on AIME.",
                "url": "https://x.com/karpathy/status/1899999999999999999",
                "date": "2026-11-06",
            }
            assets = {"card_path": str(card_img), "video_path": None, "photos": []}

            clip_file = self.scout.build_clip_for_pick(synthetic_item, assets, tmp_path)
            self.assertTrue(clip_file.exists())
            self.assertGreater(clip_file.stat().st_size, 10_000)

            spec_yaml = tmp_path / "clip_spec.yaml"
            self.assertTrue(spec_yaml.exists())

    def test_cli_run_cron_dry_run_subprocess(self):
        """Verify executing x_scout.py --run-cron --dry-run completes cleanly with exit code 0."""
        python_bin = sys.executable
        cmd = [
            python_bin,
            str(ROOT / "scout" / "x_scout.py"),
            "--run-cron",
            "--dry-run",
            "--limit",
            "1",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        self.assertEqual(res.returncode, 0, f"Process failed with stderr:\n{res.stderr}")
        self.assertIn("STARTING AUTOMATED CLOUD CRON SCOUT CYCLE", res.stdout)
        self.assertIn("[CRON COMPLETE]", res.stdout)


    def test_hook_archetypes_and_entity_timing(self):
        """Verify dynamic hook selection across Benchmark, Stakes, and Disruption archetypes."""
        # 1. Benchmark Clash
        bench_item = {
            "author_name": "DeepSeek AI",
            "text": "DeepSeek-R1 achieves 93.2% on SWE-bench and matches o1 on AIME math evals.",
        }
        res_bench = x_scout.generate_hook_and_script(bench_item)
        self.assertIn("Shatters AI Benchmarks", res_bench["title"])
        self.assertTrue(res_bench["narration_text"].startswith("DeepSeek AI just shattered frontier benchmarks"))
        self.assertIn("Can open-weight models permanently overtake proprietary frontiers?", res_bench["question"])
        words = res_bench["narration_text"].split()
        self.assertIn("DeepSeek", words[:4])
        self.assertNotIn("announced:", res_bench["narration_text"])

        # 2. Direct Stakes / Loss Aversion
        dev_item = {
            "author_name": "Cursor Team",
            "text": "Announcing new multi-agent terminal workflow tool that codes full repositories in seconds.",
        }
        res_dev = x_scout.generate_hook_and_script(dev_item)
        self.assertIn("Automates Developer Workflows", res_dev["title"])
        self.assertIn("If you are still writing code the old way, stop.", res_dev["narration_text"])
        self.assertIn("Cursor Team", res_dev["narration_text"][:80])
        self.assertNotIn("announced:", res_dev["narration_text"])

        # 3. Disruption / Breakthrough
        breakthrough_item = {
            "author_name": "Mistral AI",
            "text": "Releasing new 128k context reasoning architecture weights under Apache 2.0 license.",
        }
        res_bt = x_scout.generate_hook_and_script(breakthrough_item)
        self.assertIn("Drops Major Open Breakthrough", res_bt["title"])
        self.assertTrue(res_bt["narration_text"].startswith("Mistral AI just dropped a major technical breakthrough"))
        self.assertNotIn("announced:", res_bt["narration_text"])


if __name__ == "__main__":
    unittest.main()
