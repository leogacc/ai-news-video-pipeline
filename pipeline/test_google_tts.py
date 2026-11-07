#!/usr/bin/env python3
"""Unit tests for Google Cloud TTS integration and 3-Layer Zero-Spend Defense (pipeline/google_tts.py)."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))

import google_tts


class TestGoogleTTS(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_quota_file = Path(self.tmp_dir.name) / ".gcp_tts_quota.json"
        self._orig_quota_file = google_tts.QUOTA_FILE
        google_tts.QUOTA_FILE = self.tmp_quota_file

    def tearDown(self):
        google_tts.QUOTA_FILE = self._orig_quota_file
        self.tmp_dir.cleanup()

    def test_build_ssml_with_marks(self):
        """Verify SSML generation wraps words in <mark> tags and escapes XML entities."""
        text = "DeepSeek & OpenAI: <breakthrough> models!"
        ssml, tokens = google_tts.build_ssml_with_marks(text)

        self.assertTrue(ssml.startswith("<speak>"))
        self.assertTrue(ssml.endswith("</speak>"))
        self.assertIn('<mark name="w0"/>DeepSeek', ssml)
        self.assertIn('<mark name="w1"/>&amp;', ssml)
        self.assertIn('<mark name="w2"/>OpenAI:', ssml)
        self.assertIn('<mark name="w3"/>&lt;breakthrough&gt;', ssml)
        self.assertEqual(len(tokens), 5)
        self.assertEqual(tokens[0], "DeepSeek")
        self.assertEqual(tokens[1], "&")

    def test_quota_tracker_persistence(self):
        """Verify local quota tracking records and persists character counts."""
        usage = google_tts.get_quota_usage()
        self.assertEqual(usage["characters_used"], 0)
        self.assertEqual(usage["limit"], google_tts.MAX_MONTHLY_CHARS)

        # Record 450 characters
        new_total = google_tts.record_quota_usage(450)
        self.assertEqual(new_total, 450)
        self.assertTrue(self.tmp_quota_file.exists())

        # Record another 300 characters
        new_total2 = google_tts.record_quota_usage(300)
        self.assertEqual(new_total2, 750)

        usage2 = google_tts.get_quota_usage()
        self.assertEqual(usage2["characters_used"], 750)

    def test_zero_spend_guard_blocks_over_limit(self):
        """Verify 800,000 character hard ceiling triggers zero-spend guard."""
        # Set quota to 799,900 chars
        google_tts.record_quota_usage(799_900)

        # Asking for 50 chars is fine (799,950 <= 800,000)
        with patch.dict(os.environ, {"GOOGLE_TTS_API_KEY": "fake_test_key"}):
            allowed, reason = google_tts.can_use_google_tts(50)
            self.assertTrue(allowed)
            self.assertEqual(reason, "OK")

            # Asking for 200 chars breaches the 800k limit
            allowed_over, reason_over = google_tts.can_use_google_tts(200)
            self.assertFalse(allowed_over)
            self.assertIn("Monthly quota limit reached", reason_over)

    def test_fallback_to_kokoro_on_missing_credentials(self):
        """When GCP credentials are not configured, seamlessly fall back to Kokoro TTS."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure no GCP env vars
            os.environ.pop("GOOGLE_TTS_API_KEY", None)
            os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)

            wav, words, dur, engine = google_tts.synthesize_speech(
                "Short test sentence for Kokoro fallback.",
                allow_fallback=True,
            )

            self.assertEqual(engine, "kokoro_fallback")
            self.assertIsInstance(wav, np.ndarray)
            self.assertGreater(len(wav), 0)
            self.assertGreater(len(words), 0)
            self.assertGreater(dur, 0.5)

    def test_mock_google_tts_success(self):
        """When GCP API key is set and REST call succeeds, verify engine returns google_tts."""
        mock_wav = np.zeros(24000 * 3, dtype=np.float32)
        mock_words = [("OpenAI", 0.1, 0.5), ("released", 0.52, 0.9), ("o1", 0.95, 1.4)]

        with patch.dict(os.environ, {"GOOGLE_TTS_API_KEY": "test_valid_key"}):
            with patch("google_tts._synthesize_via_rest", return_value=(mock_wav, mock_words, 3.0)):
                wav, words, dur, engine = google_tts.synthesize_speech(
                    "OpenAI released o1.",
                    voice_name="en-US-Studio-Q",
                    speaking_rate=1.03,
                )

                self.assertEqual(engine, "google_tts")
                self.assertEqual(dur, 3.0)
                self.assertEqual(len(words), 3)
                # Verify quota incremented by string length (19 characters)
                usage = google_tts.get_quota_usage()
                self.assertEqual(usage["characters_used"], 19)

    def test_default_voice_and_speaking_rate(self):
        """Verify default voice is Studio-Q male and calibrated speaking rate is 1.03x."""
        self.assertEqual(google_tts.DEFAULT_SPEAKING_RATE, 1.03)
        self.assertEqual(google_tts.DEFAULT_VOICE, "en-US-Studio-Q")


if __name__ == "__main__":
    unittest.main()
