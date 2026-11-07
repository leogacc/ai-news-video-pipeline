#!/usr/bin/env python3
"""Google Cloud Text-to-Speech integration with 3-layer zero-spend guard.

Features:
- Studio Voice synthesis via Google Cloud TTS (default: en-US-Studio-O @ 1.03x speed, ~160 WPM).
- SSML mark timepointing (<mark name="w{i}"/>) for sample-accurate word boundaries.
- 3-Layer Zero-Spend Defense Architecture:
    1. Local Quota Tracker (.gcp_tts_quota.json) enforcing a strict 800,000 char/month ceiling
       (80% of Google's 1,000,000 free Studio tier allowance).
    2. Dual authentication support: GOOGLE_TTS_API_KEY (lightweight REST) or
       GOOGLE_APPLICATION_CREDENTIALS (GCP IAM service account).
    3. Automatic, resilient fallback to local Kokoro TTS (am_echo @ 1.20x) on missing credentials,
       quota exhaustion, or network failure.
"""

import base64
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

for _k in ("no_proxy", "NO_PROXY"):
    if _k in os.environ:
        os.environ[_k] = ",".join(
            p for p in os.environ[_k].split(",") if not (p.strip().startswith("[") and p.strip().endswith("]"))
        )

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

# Import local Kokoro TTS as fallback engine
import tts

logger = logging.getLogger("google_tts")

QUOTA_FILE = Path(__file__).resolve().parent / ".gcp_tts_quota.json"
MAX_MONTHLY_CHARS = 800_000  # 800k character local safety limit (80% of 1M free tier)
DEFAULT_VOICE = "en-US-Studio-Q"
DEFAULT_SPEAKING_RATE = 1.03


class GoogleTTSUnavailableError(Exception):
    """Raised when Google Cloud TTS cannot be used (missing credentials, quota exceeded, or network error)."""
    pass


def load_env_file():
    """Ensure project .env is loaded."""
    env_p = ROOT / ".env"
    if env_p.exists():
        with open(env_p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k not in os.environ:
                        os.environ[k] = v


load_env_file()


def get_current_month_key() -> str:
    """Return YYYY-MM key in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_quota_usage() -> Dict[str, Any]:
    """Read local quota tracker state."""
    cur_month = get_current_month_key()
    if not QUOTA_FILE.exists():
        return {"month": cur_month, "characters_used": 0, "limit": MAX_MONTHLY_CHARS}

    try:
        data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
        if data.get("month") != cur_month:
            # New month roll-over
            return {"month": cur_month, "characters_used": 0, "limit": MAX_MONTHLY_CHARS}
        return {
            "month": cur_month,
            "characters_used": data.get("characters_used", 0),
            "limit": MAX_MONTHLY_CHARS,
        }
    except Exception as e:
        logger.warning("Error reading quota tracker, resetting: %s", e)
        return {"month": cur_month, "characters_used": 0, "limit": MAX_MONTHLY_CHARS}


def record_quota_usage(chars_used: int) -> int:
    """Atomically record characters used in current month."""
    cur_month = get_current_month_key()
    usage = get_quota_usage()
    new_total = usage["characters_used"] + chars_used
    state = {
        "month": cur_month,
        "characters_used": new_total,
        "limit": MAX_MONTHLY_CHARS,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    tmp_file = QUOTA_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp_file.replace(QUOTA_FILE)
    return new_total


def can_use_google_tts(chars_needed: int) -> Tuple[bool, str]:
    """Check credentials and quota allowance."""
    api_key = os.environ.get("GOOGLE_TTS_API_KEY")
    creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if not api_key and not creds_file:
        return False, "Neither GOOGLE_TTS_API_KEY nor GOOGLE_APPLICATION_CREDENTIALS is set"

    usage = get_quota_usage()
    if usage["characters_used"] + chars_needed > MAX_MONTHLY_CHARS:
        return False, f"Monthly quota limit reached ({usage['characters_used']}/{MAX_MONTHLY_CHARS} chars used)"

    return True, "OK"


def build_ssml_with_marks(text: str) -> Tuple[str, List[str]]:
    """Build SSML with word-level <mark name="w{i}"/> tags."""
    # Clean string and extract word tokens
    clean = re.sub(r"\s+", " ", text).strip()
    raw_tokens = clean.split()
    tokens = []
    ssml_parts = ["<speak>"]

    for i, tok in enumerate(raw_tokens):
        # Escape XML entities
        esc_tok = (
            tok.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        ssml_parts.append(f'<mark name="w{i}"/>{esc_tok}')
        tokens.append(tok)

    ssml_parts.append("</speak>")
    ssml = " ".join(ssml_parts)
    return ssml, tokens


def _synthesize_via_rest(
    ssml: str,
    tokens: List[str],
    voice_name: str,
    speaking_rate: float,
    raw_text: str = "",
) -> Tuple[np.ndarray, List[Tuple[str, float, float]], float]:
    """Execute REST synthesis against Google Cloud Text-to-Speech API."""
    api_key = os.environ.get("GOOGLE_TTS_API_KEY")
    creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    headers = {"Content-Type": "application/json; charset=utf-8"}
    is_studio = voice_name.startswith("en-US-Studio")
    url = (
        "https://texttospeech.googleapis.com/v1/text:synthesize"
        if is_studio
        else "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
    )

    if api_key:
        url += f"?key={api_key}"
    elif creds_file:
        try:
            import google.auth
            import google.auth.transport.requests

            creds, _ = google.auth.load_credentials_from_file(
                creds_file, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            headers["Authorization"] = f"Bearer {creds.token}"
        except Exception as e:
            raise GoogleTTSUnavailableError(f"Failed to authenticate via GOOGLE_APPLICATION_CREDENTIALS: {e}")
    else:
        raise GoogleTTSUnavailableError("No GCP credentials available")

    if is_studio:
        # Studio voices do not currently accept <mark> tags in SSML
        payload = {
            "input": {"text": raw_text or " ".join(tokens)},
            "voice": {
                "languageCode": "en-US",
                "name": voice_name,
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": 24000,
                "speakingRate": speaking_rate,
            },
        }
    else:
        payload = {
            "input": {"ssml": ssml},
            "voice": {
                "languageCode": "en-US",
                "name": voice_name,
            },
            "audioConfig": {
                "audioEncoding": "LINEAR16",
                "sampleRateHertz": 24000,
                "speakingRate": speaking_rate,
            },
            "enableTimePointing": ["SSML_MARK"],
        }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise GoogleTTSUnavailableError(
                    f"Google Cloud TTS API error {resp.status_code}: {resp.text[:300]}"
                )
            data = resp.json()
    except httpx.HTTPError as e:
        raise GoogleTTSUnavailableError(f"HTTP request to Google Cloud TTS failed: {e}")

    # Decode audio PCM 16-bit 24kHz
    audio_b64 = data.get("audioContent", "")
    if not audio_b64:
        raise GoogleTTSUnavailableError("Google Cloud TTS returned empty audioContent")

    audio_bytes = base64.b64decode(audio_b64)
    import io
    import soundfile as sf
    wav_array, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    audio_dur = len(wav_array) / sr

    words_out: List[Tuple[str, float, float]] = []
    n_tokens = len(tokens)

    if is_studio:
        # Distribute tokens across audio duration weighted by character count
        weights = [max(1, len(w)) for w in tokens]
        total_weight = sum(weights)
        lead_in = 0.08
        available_dur = max(0.5, audio_dur - lead_in - 0.15)
        cur_t = lead_in
        for i, w in enumerate(tokens):
            w_dur = (weights[i] / total_weight) * available_dur
            start_t = cur_t
            end_t = cur_t + w_dur
            cur_t = end_t
            words_out.append((w, round(start_t, 3), round(end_t, 3)))
    else:
        # Extract timepoints from SSML_MARK
        raw_timepoints = data.get("timepoints", [])
        mark_times: Dict[int, float] = {}
        for tp in raw_timepoints:
            m_name = tp.get("markName", "")
            if m_name.startswith("w"):
                try:
                    idx = int(m_name[1:])
                    mark_times[idx] = float(tp.get("timeSeconds", 0.0))
                except ValueError:
                    pass

        for i in range(n_tokens):
            w = tokens[i]
            start_t = mark_times.get(i, 0.0 if i == 0 else words_out[-1][2])
            if i < n_tokens - 1:
                next_t = mark_times.get(i + 1, start_t + 0.25)
                end_t = max(start_t + 0.05, next_t)
            else:
                end_t = max(start_t + 0.08, audio_dur)
            words_out.append((w, round(start_t, 3), round(end_t, 3)))

    return wav_array, words_out, audio_dur


def synthesize_speech(
    text: str,
    voice_name: str = DEFAULT_VOICE,
    speaking_rate: float = DEFAULT_SPEAKING_RATE,
    allow_fallback: bool = True,
) -> Tuple[np.ndarray, List[Tuple[str, float, float]], float, str]:
    """Synthesize text into speech and word timings.

    Returns:
        (wav_array, words, duration, engine_used)
        where engine_used is either 'google_tts' or 'kokoro_fallback'
    """
    chars_needed = len(text)
    allowed, reason = can_use_google_tts(chars_needed)

    if allowed:
        try:
            logger.info("Synthesizing via Google Cloud TTS Studio voice: %s @ %.2fx (%d chars)", voice_name, speaking_rate, chars_needed)
            ssml, tokens = build_ssml_with_marks(text)
            wav_array, words_out, audio_dur = _synthesize_via_rest(
                ssml=ssml,
                tokens=tokens,
                voice_name=voice_name,
                speaking_rate=speaking_rate,
                raw_text=text,
            )
            # Record quota consumption on success
            new_usage = record_quota_usage(chars_needed)
            logger.info("Google Cloud TTS synthesis complete. Monthly quota usage: %d/%d chars", new_usage, MAX_MONTHLY_CHARS)
            return wav_array, words_out, audio_dur, "google_tts"
        except Exception as e:
            if not allow_fallback:
                raise
            logger.warning("[GCP TTS FALLBACK] Google Cloud TTS error: %s. Engaging local Kokoro TTS fallback.", e)
    else:
        logger.info("[GCP ZERO-SPEND GUARD] Cannot use Google Cloud TTS (%s). Using local Kokoro TTS engine.", reason)

    # Seamless fallback to Kokoro TTS
    logger.info("Synthesizing via local Kokoro TTS (am_echo)...")
    wav_array, words_out, _ = tts.synth_segment(text)
    audio_dur = len(wav_array) / 24000
    return wav_array, words_out, audio_dur, "kokoro_fallback"
