#!/usr/bin/env python3
"""PRODUCER (audio) — Kokoro TTS per segment -> narration_full.wav + timings.json
+ words.json.

Fixed voice (config) = channel identity. ~1x real-time on 2 vCPUs; a 60s
voiceover takes roughly a minute.

Word timing WITHOUT Whisper (2026-10-09): Kokoro's KPipeline exposes the
model's own duration predictor per token (MToken.start_ts/end_ts, seconds,
already speed-adjusted). We synthesize sentence-by-sentence (sentences
joined with newlines -> one audio chunk per sentence), read each token's
measured timing, group tokens into words, and align them to the script's
words with difflib. Result: words.json with script-faithful words and
TTS-measured timings — no re-transcription pass, no misheard product
names, no 3-minute CPU Whisper run.

Fingerprint cache: segment audio+words keyed by sha1(text+voice+speed+lang).
Unchanged scripts skip TTS entirely on re-render.
"""
import difflib
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

# 2026-10-18 TTS HERMETIC (root cause): Kokoro's model is cached locally
# and the pipeline must never need the network to synthesize. Without
# this, huggingface_hub builds an httpx client on first synthesis and
# crashes parsing this VM's proxy env (InvalidURL on the no_proxy
# IPv6 entries) — any cache-miss TTS run dies at the first segment.
# (Surfaced when the "Breaking!" delivery change forced a re-synth.)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
# Same root cause, second half: even in offline mode kokoro's model
# loader constructs the hub HTTP client, and this httpx version dies
# parsing the bracketed-IPv6 no_proxy entries before any request is
# made. TTS is fully offline (model cached above), so drop proxy vars
# outright instead of crashing inside URL parsing.
for _k in ("http_proxy", "https_proxy", "all_proxy", "no_proxy",
           "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
    os.environ.pop(_k, None)

import numpy as np
import soundfile as sf
import torch
import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
T = CFG["tts"]
CACHE = ROOT / "cache" / "tts"
CACHE.mkdir(parents=True, exist_ok=True)


def tighten_with_remap(data: np.ndarray, sr: int,
                       thresh_db: float = -35.0,
                       max_pause_sec: float = 0.25,
                       long_sil_sec: float = 0.6):
    """Pause-tighten audio AND return remap(t): original seconds ->
    tightened seconds, so TTS-measured word timings stay exact after
    Kokoro's sentence-end dead air is trimmed.

    Same policy as the old tighten_pauses: internal silences longer than
    `long_sil_sec` compress to `max_pause_sec`; edges keep a 0.12s breath.
    """
    if data.size == 0:
        return data, lambda t: t
    thresh = 10 ** (thresh_db / 20.0) * max(1e-6, np.abs(data).max())
    silent = np.abs(data) < thresh
    runs, start, prev = [], 0, silent[0]
    for i, s in enumerate(silent[1:], 1):
        if s != prev:
            runs.append((start, i, prev))
            start, prev = i, s
    runs.append((start, len(silent), prev))
    keep = np.ones(len(data), dtype=bool)
    max_keep = int(max_pause_sec * sr)
    min_sil = int(long_sil_sec * sr)
    edge_keep = int(0.12 * sr)
    for a, b, is_sil in runs:
        if not is_sil or (b - a) <= min_sil:
            continue
        if a == 0:
            keep[a + edge_keep:b] = False
        elif b == len(data):
            keep[a:b - edge_keep] = False
        else:
            keep[a + max_keep:b] = False
    kept = np.flatnonzero(keep)

    def remap(t_sec: float) -> float:
        # Original sample idx -> its POSITION in the tightened audio.
        # kept[j] is the original idx of tightened sample j, so the
        # tightened time of original idx i is j/sr where j = searchsorted.
        if len(kept) == 0:
            return 0.0
        j = int(np.searchsorted(kept, int(t_sec * sr), side="left"))
        return min(j, len(kept) - 1) / sr

    return data[keep], remap


def split_sentences(text: str) -> list:
    """Split narration into sentences. Conservative: terminal punctuation +
    whitespace. Commas/colons/semicolons stay inside — pacing, not bounds."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in (s.strip() for s in parts) if p]


def norm_w(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


# 2026-10-18 BREAKING DELIVERY (user): the cold-open kicker is SPOKEN as
# an exclamation ("Breaking!") — the "!" gives the voice exclamation
# energy plus a beat of pause — while every visual caption shows it with
# NO punctuation. Two text variants from the one script text: tts_text
# for synthesis, caption_text for the caption-faithful word list.
# Alignment runs on normalized forms, so "Breaking!"/"Breaking"/
# "Breaking," all anchor to the same measured timing. Robust to the
# worker writing "Breaking," / "Breaking" / "Breaking!" — any of them
# lands in the same place.
def _tts_text(text: str) -> str:
    t = re.sub(r"^Breaking,\s*", "Breaking! ", text)
    t = re.sub(r"^Breaking\s+", "Breaking! ", t)
    return t


def _caption_text(text: str) -> str:
    return re.sub(r"^Breaking[,.!]\s*", "Breaking ", text)


def tokens_to_words(toklist):
    """Group misaki word-tokens into Whisper-style words.
    A token flagged whitespace=True ends the word, so trailing punctuation
    attaches ('dollars' + ',' -> 'dollars,'). -> [(word, start, end)]."""
    words, cur = [], []
    for text, s, e, ws in toklist:
        if not text:
            continue
        cur.append((text, s, e))
        if ws:
            words.append(("".join(t for t, _, _ in cur),
                          cur[0][1], cur[-1][2]))
            cur = []
    if cur:
        words.append(("".join(t for t, _, _ in cur), cur[0][1], cur[-1][2]))
    return words


def align_words(script_words, tts_words):
    """Align script words to TTS-measured words. -> [(word, start, end)]
    in script order, using the SCRIPT's word text (caption-faithful) with
    the TTS timing. difflib on normalized forms handles misaki
    normalizations; unmatched script words are interpolated between
    anchored neighbors (logged)."""
    sw = script_words
    if not sw:
        return []
    if not tts_words:
        return [(w, 0.0, 0.0) for w in sw]
    ns = [norm_w(w) for w in sw]
    nt = [norm_w(w) for w, _, _ in tts_words]
    sm = difflib.SequenceMatcher(None, ns, nt, autojunk=False)
    timed = [None] * len(sw)
    for a0, b0, n in sm.get_matching_blocks():
        for k in range(n):
            if a0 + k < len(sw) and b0 + k < len(tts_words):
                _, s, e = tts_words[b0 + k]
                timed[a0 + k] = (s, e)
    matched = sum(1 for t in timed if t)
    if matched < len(sw):
        print(f"[tts] align: {matched}/{len(sw)} words anchored, "
              f"interpolating {len(sw) - matched}")
    # Fill gaps: distribute [prev_end, next_start] evenly.
    i = 0
    while i < len(sw):
        if timed[i] is not None:
            i += 1
            continue
        j = i
        while j < len(sw) and timed[j] is None:
            j += 1
        s0 = timed[i - 1][1] if i > 0 else tts_words[0][1]
        e1 = timed[j][0] if j < len(sw) else tts_words[-1][2]
        n = j - i
        step = (e1 - s0) / n if n and e1 > s0 else 0
        for k in range(n):
            timed[i + k] = (s0 + k * step, s0 + (k + 1) * step)
        i = j
    return [(w, round(s, 3), round(e, 3))
            for w, (s, e) in zip(sw, timed)]


def fingerprint(text: str) -> str:
    # 2026-10-18: "code" versions the synthesis behavior itself. The
    # Breaking!-chunk merge below changed the audio for identical text —
    # without a key change the cold open would serve the stale two-chunk
    # delivery from cache forever.
    # 2026-11-03: code 3 — warm-up trim + comma pauses change the audio.
    # code 4 — comma-pause detector correction (thresh/window/run).
    # 2026-11-05: code 5 — comma-pause detector window starts AT the
    # word end (pre-end fricative tails no longer count as pause).
    key = json.dumps({"t": text, "v": T["voice"], "s": T.get("speed", 1.0),
                      "l": T["lang_code"], "sr": T["sample_rate"],
                      "code": 5},
                     sort_keys=True)
    return hashlib.sha1(key.encode()).hexdigest()[:16]


_PIPE = None


def _pipeline():
    """Lazy singleton — the Kokoro model loads once per process, not once
    per segment."""
    global _PIPE
    if _PIPE is None:
        from kokoro import KPipeline
        _PIPE = KPipeline(lang_code=T["lang_code"])
    return _PIPE


# 2026-11-03 FIRST-WORD ONSET + COMMA PAUSES (user: the voice sometimes
# skips a sentence's first word, and sometimes rushes past a comma).
# Root causes, both measured on the 2026-11-03 PLE clip:
# - Kokoro renders a segment's FIRST token with a soft onset: the first
#   ~40ms of a segment-initial word is digital silence, so a short first
#   word ("The" 75ms, "It's" 125ms) is inaudible on a phone speaker and
#   sounds skipped. Mid-sentence words attack cleanly. Fix: synthesize
#   with a disposable discourse marker ("Well,") absorbing the soft
#   onset, then trim it — the real first word then starts at full
#   energy (verified: "the" attacks in its first 20ms window).
# - Kokoro pauses after SOME commas (first list item, clause commas)
#   but rushes past others (later list items, appositives: "layouts,",
#   "switchboards,", "electrical,", "civil,", "model," all measured
#   with no >=0.12s silence). Fix: after alignment, splice 0.22s of
#   silence after every comma that lacks a pause, shifting later
#   word times. Existing pauses are left untouched.
_WARMUPS = ["Well,", "Okay,", "Hmm,"]
_COMMA_PAUSE_SEC = 0.22
_LEAD_SILENCE_SEC = 0.12
_FADE_MS = 5


def _pick_warmup(caption_input: str) -> str:
    words = caption_input.split()
    first = words[0].strip(",.!?;:") if words else ""
    for w in _WARMUPS:
        if norm_w(w) != norm_w(first):
            return w
    return _WARMUPS[0]


def _synth_chunks(pipeline, input_text: str, sr: int):
    """Run Kokoro on input_text, tighten each chunk. -> (wav, tts_words,
    n_results). tts_words are word-level (word, start, end) in
    concatenated time."""
    wav_parts, tts_words = [], []
    t = 0.0
    n_results = 0
    for res in pipeline(input_text, voice=T["voice"],
                        speed=T.get("speed", 1.0)):
        n_results += 1
        audio = res.audio
        if audio is None:
            continue
        raw = (audio.numpy() if torch.is_tensor(audio)
               else np.asarray(audio, dtype=np.float32))
        raw = np.asarray(raw, dtype=np.float32).reshape(-1)
        tight, remap = tighten_with_remap(raw, sr)
        toks = []
        for tk in (res.tokens or []):
            if not getattr(tk, "phonemes", None) \
                    or not hasattr(tk, "start_ts"):
                continue
            toks.append((tk.text, remap(float(tk.start_ts)),
                         remap(float(tk.end_ts)), bool(tk.whitespace)))
        for w, s, e in tokens_to_words(toks):
            tts_words.append((w, round(t + s, 3), round(t + e, 3)))
        wav_parts.append(tight)
        t += len(tight) / sr
    wav = (np.concatenate(wav_parts) if wav_parts
           else np.zeros(sr, dtype=np.float32))
    return wav, tts_words, n_results


def _trim_warmup(wav, tts_words, warmup, sr):
    """Drop the warm-up word from audio + word list. Returns (wav, words)
    or None if the warm-up word is not the first token — the caller then
    falls back to plain synthesis, so warm-up audio is never shipped."""
    if not tts_words or len(tts_words) < 2:
        return None
    if norm_w(tts_words[0][0]) != norm_w(warmup):
        return None
    cut = tts_words[1][1]
    idx = int(round(cut * sr))
    if idx <= 0 or idx >= len(wav):
        return None
    out = wav[idx:].copy()
    # 5ms raised-cosine fade-in kills the splice click; inaudible.
    nfade = max(1, int(_FADE_MS / 1000.0 * sr))
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, nfade))
    out[:nfade] *= ramp
    lead = np.zeros(int(_LEAD_SILENCE_SEC * sr), dtype=np.float32)
    out = np.concatenate([lead, out])
    shift = _LEAD_SILENCE_SEC - cut
    words = [(w, round(s + shift, 3), round(e + shift, 3))
             for w, s, e in tts_words[1:]]
    return out, words


def _has_pause(wav, sr, b, thresh=0.005):
    """True if a >=0.15s near-silent run starts at/after boundary b (seconds).

    2026-11-03 detector correction (v3 lesson): the first version used
    thresh 0.015 and window [b-0.20, b+0.10] — wide enough to chain the
    previous word gap + a fricative tail (0.011-0.015) into a fake
    >=0.12s "pause", so it skipped insertion for commas whose real
    pause was only ~0.08s (PLE v3 "layouts,"). Then: thresh 0.005
    (true pause floors are 0.000-0.005; audible tails are 0.01+) and
    window [b-0.10, b+0.30] (a full word away from the previous gap).
    2026-11-05 detector correction (v2026.11.05.1, traced on the Nov 5
    cyber clip): the [b-0.10, b+0.30] window still counts up to 0.10s
    of the word's OWN quiet fricative tail as pause — a word ending in
    a quiet tail ("itself", "first", "real") can chain its pre-end
    quiet with a short real pause to reach 0.15s, so the detector
    skipped insertion while the real post-word silence was only
    0.04-0.12s (9 of 13 commas on the cyber clip's first check; the
    verdict was even phase-sensitive at the boundary, flipping between
    b=6.808 and b=6.81). Now the window starts AT b: [b, b+0.30] —
    only silence after the word end counts. A >=0.15s span below
    -46dB after the word IS a pause by definition, so skipping then
    is correct; anything shorter gets the inserted 0.22s."""
    lo = max(0, int(b * sr))
    hi = min(len(wav), int((b + 0.30) * sr))
    seg = np.abs(wav[lo:hi])
    win = max(1, int(0.02 * sr))
    n = len(seg) // win
    if n == 0:
        return False
    rms = np.sqrt(np.mean(seg[:n * win].reshape(n, win) ** 2, axis=1))
    run = 0
    for r in rms:
        run = run + 1 if r < thresh else 0
        if run * 0.02 >= 0.15:
            return True
    return False


def _splice_silence(wav, sr, b, dur):
    """Insert dur seconds of silence at the zero-crossing nearest b,
    with 2ms fades on both audio edges to avoid clicks."""
    idx = int(round(b * sr))
    lo = max(1, idx - int(0.04 * sr))
    hi = min(len(wav) - 1, idx + int(0.04 * sr))
    best, bestv = idx, None
    for j in range(lo, hi + 1):
        v = abs(wav[j])
        if bestv is None or v < bestv:
            best, bestv = j, v
    j = best
    nfade = max(1, int(0.002 * sr))
    left = wav[:j].copy()
    right = wav[j:].copy()
    if len(left) >= nfade:
        left[-nfade:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nfade)))
    if len(right) >= nfade:
        right[:nfade] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, nfade)))
    sil = np.zeros(int(round(dur * sr)), dtype=np.float32)
    return np.concatenate([left, sil, right])


def _ensure_comma_pauses(wav, words, sr):
    """Splice a pause after every comma lacking one. Words are
    (word, start, end); returns (wav, words) with later times shifted."""
    out_words = []
    shift = 0.0
    for w, s, e in words:
        s2, e2 = round(s + shift, 3), round(e + shift, 3)
        out_words.append((w, s2, e2))
        if w.endswith(","):
            if not _has_pause(wav, sr, e2):
                wav = _splice_silence(wav, sr, e2, _COMMA_PAUSE_SEC)
                shift += _COMMA_PAUSE_SEC
    return wav, out_words


def synth_segment(text: str):
    """-> (wav, words, sentences), all segment-relative.

    words: [(word, start, end)] — script words, TTS-measured timings.
    sentences: [{text, start, duration}] sliced from the word stream.

    The cold-open "Breaking" is synthesized from the exclaimed variant
    (_tts_text) and captioned from the punctuation-free variant
    (_caption_text); see above.

    2026-11-03: warm-up trim (first-word onset) + comma-pause guarantee
    run inside every synthesis; see helpers above.
    """
    tts_input = _tts_text(text)
    caption_input = _caption_text(text)
    pipeline = _pipeline()
    sents = split_sentences(tts_input)
    # 2026-10-18 VOICE CONTINUITY (user: the exclaimed "Breaking!"
    # sounded like a different voice): as its own synthesis chunk Kokoro
    # resets prosody for the one-word exclamation. Keep it in the SAME
    # chunk as the sentence that follows — the "!" still buys exclamation
    # energy + a pause, but the voice stays continuous.
    if len(sents) > 1 and sents[0].rstrip() == "Breaking!":
        sents = ["Breaking! " + sents[1]] + sents[2:]
    sr = T["sample_rate"]
    script_words = caption_input.split()
    warmup = _pick_warmup(caption_input)
    wav, tts_words, n_results = _synth_chunks(
        pipeline, warmup + " " + "\n".join(sents), sr)
    trimmed = _trim_warmup(wav, tts_words, warmup, sr)
    if trimmed is None:
        # Warm-up word did not come out first — never ship it.
        print("[tts] warm-up trim failed, plain synthesis fallback")
        wav, tts_words, n_results = _synth_chunks(
            pipeline, "\n".join(sents), sr)
    else:
        wav, tts_words = trimmed
    if not tts_words or n_results == 0:
        print("[tts] WARNING: no TTS token timings — even word distribution")
        step = (len(wav) / sr) / max(1, len(script_words))
        words = [(w, round(i * step, 3), round((i + 1) * step, 3))
                 for i, w in enumerate(script_words)]
    else:
        words = align_words(script_words, tts_words)
        wav, words = _ensure_comma_pauses(wav, words, sr)
    sentences, wi = [], 0
    for sent in sents:
        n = len(sent.split())
        chunk = words[wi:wi + n]
        wi += n
        if chunk:
            s0, e1 = chunk[0][1], chunk[-1][2]
        else:
            s0, e1 = 0.0, 0.0
        sentences.append({"text": sent, "start": round(s0, 3),
                          "duration": round(max(0.0, e1 - s0), 3)})
    return wav, words, sentences


def seg_wav(text: str, out: Path):
    """Synthesize a segment, using the fingerprint cache on a hit.

    Returns (sentences, words, hit) — segment-relative timings.
    """
    # Fingerprint on the TTS input (2026-10-18): the "Breaking!" delivery
    # transform changes the synthesized audio, so it must change the
    # cache key — otherwise the cold open would serve stale flat audio.
    fp = fingerprint(_tts_text(text))
    cached, meta_p = CACHE / f"{fp}.wav", CACHE / f"{fp}.json"
    if cached.exists() and cached.stat().st_size > 1000 \
            and meta_p.exists():
        shutil.copyfile(cached, out)
        meta = json.loads(meta_p.read_text())
        print(f"[tts] cache HIT {out.name} (fp {fp})")
        return meta["sentences"], meta["words"], True
    wav, words, sentences = synth_segment(text)
    sf.write(str(out), wav, T["sample_rate"])
    sf.write(str(cached), wav, T["sample_rate"])
    meta_p.write_text(json.dumps({"words": words, "sentences": sentences}))
    print(f"[tts] cache MISS {out.name} — synthesized + cached (fp {fp})")
    return sentences, words, False


def wav_duration(p: Path) -> float:
    return sf.info(str(p)).duration


def main():
    script = json.loads((ROOT / "output" / "script.json").read_text())
    segs = script["segments"]
    audio_dir = ROOT / "output" / "audio"
    audio_dir.mkdir(exist_ok=True)

    timings, all_words = [], []
    sr = T["sample_rate"]
    gap = int(T["segment_gap_sec"] * sr)
    full = []
    t = 0.0
    hits = 0
    for i, seg in enumerate(segs):
        p = audio_dir / f"seg_{i:02d}.wav"
        sentences, words, hit = seg_wav(seg["text"], p)
        hits += hit
        dur = wav_duration(p)
        data, _ = sf.read(str(p))
        full.append(data)
        full.append(np.zeros(gap, dtype=data.dtype))
        # Segment-relative -> absolute narration timings.
        abs_sents = [{**s, "start": round(s["start"] + t, 3)}
                     for s in sentences]
        for w, s, e in words:
            all_words.append({"word": w, "start": round(s + t, 3),
                              "end": round(e + t, 3)})
        timings.append({"segment": i, "start": round(t, 3),
                        "duration": round(dur, 3),
                        "sentences": abs_sents})
        t += dur + T["segment_gap_sec"]
        print(f"[tts] seg {i}: {dur:.1f}s, {len(words)} words, "
              f"{len(abs_sents)} sentences")

    narration = np.concatenate(full)
    out_wav = ROOT / "output" / "narration_full.wav"
    sf.write(str(out_wav), narration, sr)
    (ROOT / "output" / "timings.json").write_text(json.dumps(timings, indent=2))
    (ROOT / "output" / "words.json").write_text(json.dumps(all_words, indent=1))
    print(f"[tts] narration_full.wav ({len(narration)/sr:.1f}s), "
          f"{len(all_words)} words, {hits}/{len(segs)} segments from cache")


if __name__ == "__main__":
    main()
