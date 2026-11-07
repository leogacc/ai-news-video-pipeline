"""Unit tests for Free X Search and Ingestion Engine (pipeline/x_search.py)."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import x_search


class TestXSearch(unittest.TestCase):
    def test_fetch_user_timeline(self):
        tweets = x_search.fetch_user_timeline("sama", max_tweets=3)
        self.assertIsInstance(tweets, list)
        self.assertGreater(len(tweets), 0)
        t = tweets[0]
        self.assertIn("id", t)
        self.assertEqual(t["author_handle"], "sama")
        self.assertIn("text", t)
        self.assertIn("url", t)
        self.assertTrue(t["author_verified"])

    def test_search_google_news_x(self):
        hits = x_search.search_google_news_x("OpenAI", max_results=3)
        self.assertIsInstance(hits, list)
        self.assertGreater(len(hits), 0)
        h = hits[0]
        self.assertIn("title", h)
        self.assertIn("link", h)

    def test_search_hn_dispatches(self):
        hits = x_search.search_hn_ai_dispatches("DeepSeek", max_results=3)
        self.assertIsInstance(hits, list)
        self.assertGreater(len(hits), 0)
        h = hits[0]
        self.assertIn("title", h)
        self.assertIn("url", h)

    def test_hydrate_tweet_details_text(self):
        # Sam Altman tweet
        details = x_search.hydrate_tweet_details("1889059531625464090", handle="sama")
        self.assertEqual(details["id"], "1889059531625464090")
        self.assertEqual(details["author"]["screen_name"], "sama")
        self.assertTrue(details["author"]["verified"])
        self.assertIn("buy twitter", details["text"].lower())
        self.assertGreater(details["metrics"]["likes"], 10000)

    def test_hydrate_tweet_details_video(self):
        # OpenAI video tweet
        details = x_search.hydrate_tweet_details("2114780711664398349", handle="OpenAI")
        self.assertEqual(details["author"]["screen_name"], "OpenAI")
        self.assertEqual(details["author"]["badge_type"], "organization")
        self.assertGreater(len(details["videos"]), 0)
        v = details["videos"][0]
        self.assertIsNotNone(v.get("best_mp4"))
        self.assertTrue(v["best_mp4"].startswith("https://video.twimg.com/"))

    def test_dedupe_check(self):
        state = {"seen_post_ids": ["123", "456"]}
        saved = [{"post_id": "789"}]
        clipped = [{"post_id": "999"}]

        self.assertTrue(x_search.dedupe_check("123", state, saved, clipped))
        self.assertTrue(x_search.dedupe_check("789", state, saved, clipped))
        self.assertTrue(x_search.dedupe_check("999", state, saved, clipped))
        self.assertFalse(x_search.dedupe_check("000", state, saved, clipped))


if __name__ == "__main__":
    unittest.main()
