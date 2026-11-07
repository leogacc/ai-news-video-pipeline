"""Unit tests for official X-post dark-mode card rendering (pipeline/tweet_card.py)."""
import os
import sys
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import tweet_card


class TestTweetCard(unittest.TestCase):
    def test_tweet_id(self):
        handle, sid = tweet_card._tweet_id("https://x.com/OpenAI/status/2114780711664398349")
        self.assertEqual(handle, "OpenAI")
        self.assertEqual(sid, "2114780711664398349")

        handle2, sid2 = tweet_card._tweet_id("https://twitter.com/sama/status/1889059531625464090?s=20")
        self.assertEqual(handle2, "sama")
        self.assertEqual(sid2, "1889059531625464090")

        with self.assertRaises(ValueError):
            tweet_card._tweet_id("https://github.com/leogacc")

    def test_fmt_count(self):
        self.assertEqual(tweet_card._fmt_count(0), "0")
        self.assertEqual(tweet_card._fmt_count(None), "")
        self.assertEqual(tweet_card._fmt_count(450), "450")
        self.assertEqual(tweet_card._fmt_count(216912), "216.9K")
        self.assertEqual(tweet_card._fmt_count(3200000), "3.2M")

    def test_fmt_date(self):
        iso_date = "2025-02-10T21:11:04.000Z"
        formatted_iso = tweet_card._fmt_date(iso_date)
        self.assertIn("Feb 10, 2025", formatted_iso)

        tw_date = "Mon Feb 10 21:11:04 +0000 2025"
        formatted_tw = tweet_card._fmt_date(tw_date)
        self.assertIn("Feb 10, 2025", formatted_tw)

    def test_badge_svg(self):
        gold = tweet_card._badge_svg("organization")
        self.assertIn(tweet_card.GOLD, gold)
        blue = tweet_card._badge_svg("blue")
        self.assertIn(tweet_card.ACCENT, blue)
        none = tweet_card._badge_svg(None)
        self.assertEqual(none, "")

    def test_fetch_syndication(self):
        # Sam Altman tweet
        sid = "1889059531625464090"
        t = tweet_card._fetch_syndication(sid)
        self.assertEqual(t["author"]["screen_name"], "sama")
        self.assertEqual(t["author"]["name"], "Sam Altman")
        self.assertTrue(t["author"]["verification"]["verified"])
        self.assertIn("buy twitter", t["text"])
        self.assertGreater(t["likes"], 10000)

    def test_render_tweet_card(self):
        url = "https://x.com/sama/status/1889059531625464090"
        dest = Path("/tmp/test_unit_tweet_card.png")
        if dest.exists():
            dest.unlink()
        
        result = tweet_card.render_tweet_card(url, dest)
        self.assertTrue(result.exists())
        self.assertGreater(result.stat().st_size, 20000)

        with Image.open(result) as im:
            self.assertEqual(im.size[0], 2128)  # 1064px * 2x device scale
            self.assertGreater(im.size[1], 300)
        
        # Cleanup
        dest.unlink(missing_ok=True)
        html_file = dest.with_suffix(".html")
        html_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
