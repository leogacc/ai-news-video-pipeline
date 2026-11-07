"""Unit tests for the Codified TikTok Worthiness Scorecard (Objective 3.1).

Tests 4-pillar evaluation rubric, hard disqualifiers (plugins, hardware,
lawsuits, bugfixes), positive breakthrough cases, borderline rejections,
and Remotion visual boost.
"""

import unittest
from scout.x_scout import excitement_gate_score


class TestTikTokWorthinessScorecard(unittest.TestCase):
    def test_disqualifier_plugins_and_integrations(self):
        """Routine plugins, SDK integrations, and minor wrappers are rejected immediately."""
        item = {
            "post_id": "test_plugin_1",
            "author": "OpenAI",
            "text": "ChatGPT adds support for iCloud Mail and calendar plugin integrations today.",
            "has_media": False,
            "category": "release",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertFalse(passed)
        self.assertTrue(scores.get("disqualified"))
        self.assertEqual(scores.get("total"), 0)
        self.assertIn("Routine integration / plugin", reason)

    def test_disqualifier_hardware_without_ai_paradigm(self):
        """Hardware launches without AI paradigm shifts are disqualified (e.g. XREAL Aura)."""
        item = {
            "post_id": "test_xreal_1",
            "author": "tech_insider",
            "text": "XREAL launches Aura smart glasses pre-order at $1,099 with dual display spec bump.",
            "has_media": True,
            "category": "release",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertFalse(passed)
        self.assertTrue(scores.get("disqualified"))
        self.assertEqual(scores.get("total"), 0)
        self.assertIn("Hardware product launch without AI capability shift", reason)

    def test_disqualifier_legal_and_lawsuit_disputes(self):
        """Lawsuits and regulatory disputes are rejected (stakes are legal, not technical)."""
        item = {
            "post_id": "test_lawsuit_1",
            "author": "law_tracker",
            "text": "NYT sues Brave Software in federal court alleging copyright infringement and AI scraping.",
            "has_media": False,
            "category": "find",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertFalse(passed)
        self.assertTrue(scores.get("disqualified"))
        self.assertEqual(scores.get("total"), 0)
        self.assertIn("Legal / lawsuit dispute", reason)

    def test_disqualifier_routine_bugfixes_and_patches(self):
        """Routine maintenance, dependency bumps, and bugfixes are rejected."""
        item = {
            "post_id": "test_patch_1",
            "author": "dev_bot",
            "text": "v2.1.4 patch release is out! Includes minor fix and dependency bump for huggingface client.",
            "has_media": False,
            "category": "find",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertFalse(passed)
        self.assertTrue(scores.get("disqualified"))
        self.assertEqual(scores.get("total"), 0)
        self.assertIn("Routine bugfix / maintenance patch", reason)

    def test_positive_deepseek_r1_paper(self):
        """DeepSeek-R1 open reasoning paper easily clears passing bar with high scores."""
        item = {
            "post_id": "1882000000000000001",
            "author": "deepseek_ai",
            "author_handle": "deepseek_ai",
            "text": "DeepSeek-R1 technical report and paper released: breakthrough open source weights and reasoning architecture matching OpenAI o1 on SOTA AIME benchmarks! https://arxiv.org/abs/2501.12948",
            "has_media": False,
            "category": "release",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertTrue(passed)
        self.assertFalse(scores.get("disqualified"))
        self.assertGreaterEqual(scores["total"], 34)
        self.assertGreaterEqual(scores["hook"], 8)
        self.assertGreaterEqual(scores["educational"], 8)
        self.assertGreaterEqual(scores["stakes"], 8)
        self.assertGreaterEqual(scores["visual"], 8)
        self.assertIn("Passed TikTok Worthiness Scorecard", reason)

    def test_positive_karpathy_hackertube(self):
        """Karpathy HackerTube find clears passing bar with high hook, educational, and visual scores."""
        item = {
            "post_id": "1882000000000000002",
            "author": "karpathy",
            "author_handle": "karpathy",
            "text": "Built a clean YouTube client HackerTube in 2 hours to filter 43M comments with zero human code using Claude 3.7. Code is open source on github.com/karpathy/hackertube",
            "has_media": True,
            "category": "find",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertTrue(passed)
        self.assertFalse(scores.get("disqualified"))
        self.assertGreaterEqual(scores["total"], 32)
        self.assertGreaterEqual(scores["hook"], 8)
        self.assertGreaterEqual(scores["educational"], 8)
        self.assertGreaterEqual(scores["visual"], 8)

    def test_positive_vip_official_release(self):
        """Official release from VIP leader clears stakes and hook requirements."""
        item = {
            "post_id": "1882000000000000003",
            "author": "Sam Altman",
            "author_handle": "sama",
            "text": "First ever public preview of o3-mini: state of the art reasoning model at 10x faster inference speed. Architecture paper on github.com.",
            "has_media": True,
            "category": "release",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertTrue(passed)
        self.assertGreaterEqual(scores["total"], 32)
        self.assertEqual(scores["stakes"], 9)
        self.assertEqual(scores["hook"], 9)

    def test_borderline_failing_meme_post(self):
        """Meme/hype post lacking educational substance fails the educational minimum bar (< 6)."""
        item = {
            "post_id": "test_meme_1",
            "author": "hype_ai",
            "text": "Craziest superintelligence vibes! AI is unbelievable lol lmao ratio",
            "has_media": False,
            "category": "find",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertFalse(passed)
        self.assertLess(scores["educational"], 6)
        self.assertIn("Below TikTok Worthiness Bar", reason)

    def test_borderline_failing_niche_config(self):
        """Narrow internal library config fails the relatable stakes minimum bar (< 6)."""
        item = {
            "post_id": "test_niche_1",
            "author": "sqlite_tooling",
            "text": "Internal niche config updates for dev environment schema formatting.",
            "has_media": False,
            "category": "find",
        }
        passed, reason, scores = excitement_gate_score(item)
        self.assertFalse(passed)
        self.assertLess(scores["stakes"], 6)

    def test_remotion_visual_boost_for_benchmark_papers(self):
        """Abstract research paper without native video gets baseline 8/10 visual score via Remotion."""
        item = {
            "post_id": "test_arxiv_1",
            "author": "researcher",
            "text": "New state of the art reasoning benchmarks on AIME and SWE-bench: technical report and paper on arxiv.org/abs/2501.99999",
            "has_media": False,  # Text/link only
            "category": "find",
        }
        passed, reason, scores = excitement_gate_score(item)
        # Visual potential must be >= 8 due to Remotion benchmark/architecture engine
        self.assertGreaterEqual(scores["visual"], 8)
        self.assertTrue(passed)


if __name__ == "__main__":
    unittest.main()
