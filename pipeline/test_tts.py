#!/usr/bin/env python3
"""Deterministic tests for pipeline/tts.py comma-pause detection.

Run: ~/workspace/ai-video-pipeline/.venv/bin/python pipeline/test_tts.py
No model, no network — synthetic signals only (sr 24000, loud 0.1,
quiet 0.0, sharp transitions; 20ms RMS bins, thresh 0.005).

Cases (all must pass):
  1. layouts-like tail + short pause -> INSERT (no pause detected)
  2. PLE-like 0.16s true pause after the word -> SKIP (pause detected)
  3. continuous speech, no gap at all -> INSERT
  4. inserted 0.22s of zeros after the word -> SKIP
  5. REGRESSION 2026-11-05 (cyber clip, "itself,"): a word ending in
     a quiet fricative tail — 0.15s of quiet BEFORE the word end plus
     only 0.06s after it. The pre-fix window [b-0.10, b+0.30] chained
     the tail into a 0.16s "pause" and skipped insertion; the fixed
     window [b, b+0.30] must see only the 0.06s after the word end
     and INSERT.
"""
import sys
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from tts import _has_pause

SR = 24000


def sig(spans):
    """spans: [(t0, t1, amp), ...] over a 2.0s signal."""
    wav = np.zeros(2 * SR, dtype=np.float32)
    for t0, t1, amp in spans:
        wav[int(t0 * SR):int(t1 * SR)] = amp
    return wav


def check(name, wav, b, expect):
    got = _has_pause(wav, SR, b)
    status = "PASS" if got == expect else "FAIL"
    print(f"[{status}] {name}: _has_pause={got} (expect {expect})")
    return got == expect


ok = True
# 1. tail + short pause: quiet 0.05s before b, 0.08s after -> INSERT
ok &= check("tail+short-pause inserts",
            sig([(0, 0.60, 0.1), (0.60, 0.73, 0.0), (0.73, 2.0, 0.1)]),
            0.65, False)
# 2. true 0.16s pause starting at b -> SKIP
ok &= check("0.16s true pause skips",
            sig([(0, 0.65, 0.1), (0.65, 0.81, 0.0), (0.81, 2.0, 0.1)]),
            0.65, True)
# 3. continuous speech -> INSERT
ok &= check("continuous speech inserts",
            sig([(0, 2.0, 0.1)]), 0.65, False)
# 4. inserted 0.22s zeros after b -> SKIP
ok &= check("inserted 0.22s zeros skip",
            sig([(0, 0.65, 0.1), (0.65, 0.87, 0.0), (0.87, 2.0, 0.1)]),
            0.65, True)
# 5. REGRESSION 2026-11-05: quiet straddles b (0.15s before, 0.06s
#    after); only 0.06s of real post-word pause -> INSERT.
ok &= check("fricative-tail straddle inserts (2026-11-05)",
            sig([(0, 0.50, 0.1), (0.50, 0.71, 0.0), (0.71, 2.0, 0.1)]),
            0.65, False)

print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
