#!/usr/bin/env python3
"""Unit tests for Phase 10.1: 5-Act Narrative Script Architecture.

Verifies:
1. 5-Act Dramatic Structure (Hook -> Evidence -> The Wall -> Secret Weapon -> Resolution & Dilemma).
2. Entity vocalized in the first 5 words (< 2.5s TikTok indexing requirement).
3. Quantified shock metric in Act 1.
4. Conflict/friction framing in Act 3.
5. Flesch-Kincaid reading grade <= 8.0 (strict ceiling <= 9.0).
6. Word count target (65-105 words, ~30-40s duration).
7. Zero-spend guarantee ($0.00) via deterministic offline heuristic fallback.
8. Backward compatibility with all legacy consumer keys.
"""
import os
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "scout"))

import write
import x_scout


class TestWrite5ActScript(unittest.TestCase):
    def setUp(self):
        # Force offline heuristic execution to guarantee $0 spend during test runs
        self.old_gemini_key = os.environ.get("GEMINI_API_KEY")
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]

    def tearDown(self):
        if self.old_gemini_key is not None:
            os.environ["GEMINI_API_KEY"] = self.old_gemini_key

    def test_benchmark_archetype_narrative_structure(self):
        """Test Benchmark Clash archetype fulfills all 5 acts and metrics."""
        find = {
            "author_name": "DeepSeek AI",
            "text": "DeepSeek-R1 achieves 93.2% on SWE-bench and matches o1 on AIME math evals.",
        }
        res = write.write_5act_script(find, use_llm=False)

        # 1. Structural assertions
        self.assertIn("script_sentences", res)
        sentences = res["script_sentences"]
        self.assertGreaterEqual(len(sentences), 6)
        self.assertIn("act_1_hook", res)
        self.assertIn("act_2_evidence", res)
        self.assertIn("act_3_conflict", res)
        self.assertIn("act_4_demo", res)
        self.assertIn("act_5_resolution", res)
        self.assertIn("question", res)

        # 2. Entity positioning (< 5 words)
        words_act1 = res["act_1_hook"].split()
        self.assertTrue(any(w in words_act1[:3] for w in ["DeepSeek", "DeepSeek-R1"]))

        # 3. Quantified shock hook (contains % or number)
        self.assertTrue(any(char.isdigit() for char in res["act_1_hook"]))
        self.assertIn("93.2%", res["act_1_hook"])

        # 4. Act 3 conflict framing
        act3_lower = res["act_3_conflict"].lower()
        self.assertTrue(any(w in act3_lower for w in ["instead of", "wall", "failed", "cannot", "bottleneck", "relying"]))

        # 5. Debate question ending
        self.assertIn("?", res["question"])
        self.assertIn("Drop your thoughts below.", res["question"])

        # 6. Word count and reading grade
        self.assertGreaterEqual(res["word_count"], 65)
        self.assertLessEqual(res["word_count"], 105)
        self.assertLessEqual(res["reading_grade"], 9.0)

        # 7. Backward compatibility
        self.assertIn("title", res)
        self.assertIn("title_prefix", res)
        self.assertIn("hook_opening", res)
        self.assertIn("narration_text", res)
        self.assertIn("clean_text", res)
        self.assertEqual(res["badge"], "NEW SOTA")

    def test_developer_workflow_archetype(self):
        """Test Developer Workflow archetype preserves prompt stakes and entity speed."""
        find = {
            "author_name": "Cursor Team",
            "text": "Announcing new multi-agent terminal workflow tool that codes full repositories in seconds.",
        }
        res = write.write_5act_script(find, use_llm=False)

        self.assertIn("Automates Developer Workflows", res["title"])
        self.assertIn("If you are still writing code the old way, stop.", res["narration_text"])
        self.assertIn("Cursor Team", res["act_1_hook"])
        self.assertTrue(any(w in res["act_3_conflict"].lower() for w in ["instead of", "bottlenecks", "manual"]))
        self.assertEqual(res["badge"], "AGENT WORKFLOW")
        self.assertLessEqual(res["reading_grade"], 8.5)

    def test_safety_and_disaster_archetype(self):
        """Test Safety & Critical Failure archetype highlights disaster and live drop table refusal."""
        find = {
            "author_name": "Alonso Network",
            "text": "AI agent dropped production database tables in 9 seconds during scheduled maintenance.",
        }
        res = write.write_5act_script(find, use_llm=False)

        self.assertIn("Critical Agent Failure", res["title"])
        self.assertIn("deleted an entire production database", res["act_1_hook"])
        self.assertIn("Alonso Network", res["act_1_hook"])
        self.assertIn("does not work", res["act_3_conflict"])
        self.assertIn("refused in real time", res["act_4_demo"])
        self.assertEqual(res["badge"], "CRITICAL FAILURE")

    def test_swarm_and_computer_use_archetype(self):
        """Test Swarm & Computer Use archetype captures parallel desktop sandboxes."""
        find = {
            "author_name": "Anthropic AI",
            "text": "Autonomous computer use swarm orchestrator executes parallel desktop workflows across VMs.",
        }
        res = write.write_5act_script(find, use_llm=False)

        self.assertIn("Coordinated AI Swarms", res["title"])
        self.assertIn("parallel swarms", res["act_1_hook"])
        self.assertIn("Instead of single-agent bottlenecks", res["act_3_conflict"])
        self.assertEqual(res["badge"], "EMERGENT TECH TREND")

    def test_reading_grade_calculation(self):
        """Verify reading grade calculation handles complex and simple text without crashing."""
        simple_text = "The quick brown fox jumps over the lazy dog. The cat slept on the mat."
        grade = write.calculate_reading_grade(simple_text)
        self.assertIsInstance(grade, float)
        self.assertLessEqual(grade, 6.0)

        complex_text = "The speculative decoding architecture employs reinforcement learning with human feedback."
        grade_comp = write.calculate_reading_grade(complex_text)
        self.assertIsInstance(grade_comp, float)
        self.assertGreater(grade_comp, grade)

    def test_x_scout_delegation_compatibility(self):
        """Verify scout/x_scout.py generate_hook_and_script seamlessly delegates to 5-act generator."""
        item = {
            "author_name": "DeepSeek AI",
            "text": "DeepSeek-R1 achieves 93.2% on SWE-bench and matches o1 on AIME math evals.",
        }
        editorial = x_scout.generate_hook_and_script(item)

        # Legacy keys check
        self.assertIn("title", editorial)
        self.assertIn("title_prefix", editorial)
        self.assertIn("hook_opening", editorial)
        self.assertIn("narration_text", editorial)
        self.assertIn("question", editorial)
        self.assertIn("clean_text", editorial)
        self.assertIn("author", editorial)

        # Phase 10 keys check
        self.assertIn("script_sentences", editorial)
        self.assertIn("act_1_hook", editorial)
        self.assertIn("act_3_conflict", editorial)
        self.assertIn("reading_grade", editorial)
        self.assertIn("word_count", editorial)
        self.assertIn("hashtags", editorial)
        self.assertEqual(len(editorial["hashtags"]), 5)


if __name__ == "__main__":
    unittest.main()
