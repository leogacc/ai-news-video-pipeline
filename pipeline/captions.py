#!/usr/bin/env python3
"""PRODUCER (captions) — TTS word timings -> terminal-style .ass.

2026-10-09 redesign (user): captions ARE a terminal. Glowing green
monospace text types itself letter-by-letter exactly as spoken, on a
background that is ALWAYS black. Captions sit at one fixed spot for the
whole video: top-middle of the bottom third (tight, no extra top
padding) — shots take up the rest of the space above.

Typing is ASS karaoke: each letter gets a chunk sized to its share of
its word's spoken duration, PLUS the pause after the word folded into
the word's last letter (2026-10-09 sync fix — without the gaps the
chunks play back-to-back and captions run progressively early through
each phrase). Error diffusion keeps the sweep landing exactly on the
phrase end. Untyped letters are fully transparent, so text appears
letter by letter as it is spoken.

Word timings come straight from the TTS stage (tts.py writes words.json
from Kokoro's own duration predictor). No Whisper re-transcription.
"""
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())

# Terminal caption design: background always black; text block top is
# pinned to CAPTION_TOP for the whole video (top-middle of bottom third).
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 68
LINE_H = int(FONT_SIZE * 1.30)          # 88
MAX_W = 1080 - 120
CAPTION_TOP = 1450                     # text block top edge, fixed (matches intro text y=1450)
GREEN = "&H0014FF39"                    # #39FF14 neon (ASS &HAABBGGRR)


def ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _font():
    try:
        return ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception:
        return ImageFont.load_default()


def wrap_word_indices(items, font) -> list:
    """Greedy word-wrap into lines of indices (keeps timings)."""
    meas = ImageDraw.Draw(Image.new("RGB", (1080, 1920)))
    widths = [meas.textlength(wd, font=font) for _, _, wd in items]
    space_w = meas.textlength(" ", font=font)
    lines, cur, cur_w = [], [], 0
    for idx, (wd_w) in enumerate(widths):
        add = wd_w if not cur else space_w + wd_w
        if cur_w + add <= MAX_W:
            cur.append(idx)
            cur_w += add
        else:
            if cur:
                lines.append(cur)
            cur, cur_w = [idx], wd_w
    if cur:
        lines.append(cur)
    return lines or [[]]


def karaoke_text(items, gaps, lines) -> str:
    """items: [(start, end, WORD)]; gaps: pause after each word;
    lines: lists of indices. Per-LETTER karaoke (2026-10-11, restored):
    the sweep reveals letter-by-letter like the intro's typewriter.
    Each letter gets an equal share of its word's spoken duration; the
    word's following pause is folded into the word's last letter so the
    timeline stays honest. Quantized with error diffusion so the total
    is exact. A "> " prompt leads the first line. Trailing spaces ride
    on each word's last letter; line breaks carry no trailing space."""
    chunks = []   # (float_cs, text, break_after)
    for li, line in enumerate(lines):
        for wi, idx in enumerate(line):
            s, e, wd = items[idx]
            gap = gaps[idx]
            if not wd:
                continue
            last_in_phrase = (li == len(lines) - 1 and wi == len(line) - 1)
            last_in_line = wi == len(line) - 1
            # Per-letter: split word duration equally across letters.
            # Last letter absorbs the following pause + trailing space.
            n_letters = len(wd)
            if n_letters == 0:
                continue
            word_dur = (e - s) * 100.0
            per_letter = word_dur / n_letters
            for ci, ch in enumerate(wd):
                is_last_letter = (ci == n_letters - 1)
                dur = per_letter
                txt = ch
                if is_last_letter:
                    dur += gap * 100.0
                    if not last_in_phrase:
                        txt += " "
                chunks.append((dur, txt,
                               is_last_letter and last_in_line
                               and not last_in_phrase))
    out = []
    err = 0.0
    for k, (raw, txt, brk) in enumerate(chunks):
        v = raw + err
        q = max(1, int(round(v)))
        err = v - q
        if k == len(chunks) - 1:
            q = max(1, q + int(round(err)))
        t = txt.replace("{", "\\{").replace("}", "\\}")
        out.append(f"{{\\k{q}}}{t}")
        if brk:
            out.append("\\N")
    # Block cursor (2026-10-11): terminal-style █ trails the typing,
    # matching the intro. Zero-duration \k so it appears with the last
    # letter and stays through the phrase.
    out.append("{\\k0}█")
    return "> " + "".join(out)


def main():
    words = json.loads((ROOT / "output" / "words.json").read_text())
    words = [(w["start"], w["end"], w["word"]) for w in words]
    words = [(s, e, w) for s, e, w in words if w]
    if not words:
        raise RuntimeError("[captions] words.json is empty")
    # The intro types its own text full-screen — no caption cards under it.
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    intro_end = (timings[0]["start"] + timings[0]["duration"]
                 if timings else 0)

    # Group into typed phrases: break at sentence end, or when a phrase
    # would exceed ~2.8s / 12 words — same cadence as the old cards.
    # Hard break at the intro boundary: the intro types its own text, so
    # the next segment's first words must not be swallowed into the
    # suppressed intro phrase.
    phrases, cur = [], []
    for s, e, w in words:
        if cur and cur[0][0] < intro_end - 0.05 <= s:
            phrases.append(cur)
            cur = []
        cur.append((s, e, w))
        ends = bool(re.search(r"[.?!:;]$", w))
        if ends or len(cur) >= 12 or (cur and e - cur[0][0] > 2.8):
            phrases.append(cur)
            cur = []
    if cur:
        phrases.append(cur)

    font = _font()
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Terminal,DejaVu Sans Mono,{FONT_SIZE},{GREEN},&HFF000000,&HFF000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,1,60,60,1450,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for pi, ph in enumerate(phrases):
        start, end = ph[0][0], ph[-1][1]
        if start < intro_end - 0.05:
            continue  # intro: the terminal intro types its own text
        # Gap before next phrase (2026-10-11): zero-gap Dialogue
        # transitions stall ffmpeg's ASS renderer — it holds the previous
        # caption and never shows the next. End 1 frame (0.04s) early to
        # force a clean switch. Per-word karaoke means the last word is
        # already visible; only its highlight is trimmed.
        if pi < len(phrases) - 1:
            next_start = phrases[pi + 1][0][0]
            end = min(end, next_start - 0.04)
        items = [(s, e, w.upper()) for s, e, w in ph]
        # Pause after each word — folded into the word's last letter by
        # karaoke_text so the typing timeline matches the speech timeline.
        gaps = [max(0.0, items[k + 1][0] - items[k][1])
                if k < len(items) - 1 else 0.0
                for k in range(len(items))]
        lines = wrap_word_indices(items, font)
        block = len(lines) * LINE_H
        # Pin the text block top to CAPTION_TOP for the whole video.
        mv = max(20, (1920 - CAPTION_TOP) - block)
        # Per-letter Dialogue lines (2026-10-12): each line shows the
        # text typed up to that letter plus block cursor, mimicking the
        # intro's frame-by-frame PIL typing. The cursor trails the typing
        # frontier, not just appearing at the end.
        # Build a flat letter sequence with line-break positions.
        flat = []  # (word_idx, char_idx, is_space_after, line_break_after)
        for li, line in enumerate(lines):
            for wi, idx in enumerate(line):
                w = items[idx][2]
                for ci in range(len(w)):
                    flat.append((idx, ci,
                                 ci == len(w) - 1 and wi < len(line) - 1,
                                 False))
                # Space after word (not after last word of phrase)
                if wi < len(line) - 1 or li < len(lines) - 1:
                    # Space is part of the word's last letter timing
                    pass
            # Line break after each line except last
            if li < len(lines) - 1:
                # Mark the last letter of this line as having a break after
                if flat:
                    idx, ci, sp, _ = flat[-1]
                    flat[-1] = (idx, ci, sp, True)
        letter_times = []  # (letter_start, letter_end, visible_text)
        # Map word_idx -> (start, end, gap)
        winfo = {k: (items[k][0], items[k][1], gaps[k])
                 for k in range(len(items))}
        # Build visible text incrementally
        typed = "> "
        for fi, (widx, cidx, sp_after, brk_after) in enumerate(flat):
            s, e, gap = winfo[widx]
            w = items[widx][2]
            n = len(w)
            per_letter = (e - s) / n if n else 0
            ls = s + cidx * per_letter
            le = s + (cidx + 1) * per_letter
            ch = w[cidx]
            typed += ch
            if cidx == n - 1:
                le += gap
                if sp_after:
                    typed += " "
            if brk_after:
                typed += "\\N"
            # Cursor trails the typed text
            visible = typed + "█"
            letter_times.append((ls, le, visible))
        # Emit Dialogue lines; last letter holds to phrase end.
        for li, (ls, le, vis) in enumerate(letter_times):
            if li == len(letter_times) - 1:
                le = end
            # 1-frame gap between letters to force ASS renderer refresh
            le = min(le, (letter_times[li+1][0] - 0.001)
                     if li < len(letter_times) - 1 else le)
            txt = vis.replace("{", "\\{").replace("}", "\\}")
            events.append(
                f"Dialogue: 0,{ts(ls)},{ts(le)},Terminal,,0,0,{mv},,{txt}")

    out = ROOT / "output" / "captions.ass"
    content = header + "\n".join(events) + "\n"
    # Atomic write (2026-10-11): write to temp then rename, so a killed
    # process never leaves a truncated ASS (which cut captions mid-sentence).
    tmp = out.with_suffix(".ass.tmp")
    tmp.write_text(content)
    tmp.rename(out)
    # Validate: every Dialogue line must be complete (no cut-off tags).
    for i, line in enumerate(content.split("\n")):
        if line.startswith("Dialogue:") and line.rstrip().endswith("{"):
            raise RuntimeError(
                f"[captions] VALIDATION FAILED: truncated Dialogue at line {i}")
    print(f"[captions] {len(words)} TTS-timed words -> {len(phrases)} typed "
          f"phrases -> {out} (validated)")


if __name__ == "__main__":
    main()
