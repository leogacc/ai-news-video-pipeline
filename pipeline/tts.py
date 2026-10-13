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
import re
import shutil
from pathlib import Path

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
    key = json.dumps({"t": text, "v": T["voice"], "s": T.get("speed", 1.0),
                      "l": T["lang_code"], "sr": T["sample_rate"]},
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


def synth_segment(text: str):
    """-> (wav, words, sentences), all segment-relative.

    words: [(word, start, end)] — script words, TTS-measured timings.
    sentences: [{text, start, duration}] sliced from the word stream.
    """
    pipeline = _pipeline()
    sents = split_sentences(text)
    sr = T["sample_rate"]
    wav_parts, tts_words = [], []
    t = 0.0
    n_results = 0
    for res in pipeline("\n".join(sents), voice=T["voice"],
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
    script_words = text.split()
    if not tts_words or n_results == 0:
        print("[tts] WARNING: no TTS token timings — even word distribution")
        step = (len(wav) / sr) / max(1, len(script_words))
        words = [(w, round(i * step, 3), round((i + 1) * step, 3))
                 for i, w in enumerate(script_words)]
    else:
        words = align_words(script_words, tts_words)
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
    fp = fingerprint(text)
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
