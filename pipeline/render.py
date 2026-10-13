#!/usr/bin/env python3
"""PRODUCER (render) — two-pass ffmpeg.

Pass 1: each segment -> 1080x1920 (or 1280x720) clip. The background is
ALWAYS black: stills are fit inside the shot region (full width, y 60 to
1280, centered) over black; clips are fit/padded the same way. Captions
live at one fixed spot — top-middle of the bottom third — for the whole
video. Stills get an elastic zoom-OUT only (fast out, decaying wobble,
settles at 1.0 so the full frame ends up shown); never a zoom-in. The
cold-open hook gets a terminal-style animated intro (green monospace
typing on black); the branding hook gets the YouTube card.
Pass 2: concat -> burn typed terminal captions (green monospace,
letter-by-letter karaoke synced to speech) -> mix narration + ducked
music bed -> loudnorm -> H.264 MP4 with faststart.

Two passes instead of one giant filtergraph: far easier to debug on a weak VM,
and a failed segment doesn't nuke a 40-minute encode.
"""
import json
import random
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())


def run(cmd):
    print("[render]", " ".join(cmd[:6]), "...")
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _load_intro_logo(p):
    """Load a logo pin for the black intro — transparency-aware.

    ROOT CAUSE FIX (2026-10-11): the old code did
    ``Image.open(p).convert("RGB")``, which DROPS the alpha channel. A
    proper logo file (white wordmark on transparent background) came out
    as a solid white box on the black intro. This loader instead:

    1. Respects alpha: transparent regions composite onto black.
    2. Auto-inverts dark marks: a dark-on-transparent logo is invisible
       on black, so the mark is inverted (alpha preserved) — this
       automates the old "invert dark logos at pin time" worker rule.
    3. Keys out opaque white backgrounds: a JPG-style white-background
       logo gets white keyed to transparent, then handled as above.
    4. Visibility guard: rejects files that are still a white box
       (<5% black pixels) or invisible (<2% non-black content) with a
       loud warning — the caller falls back to a glyph, never ships a box.

    Returns an RGB PIL image, or None if the file is unusable.
    """
    from PIL import ImageOps
    try:
        im = Image.open(p)
    except Exception as e:
        print(f"[render] WARNING: cannot open logo pin {p}: {e}")
        return None
    rgba = im.convert("RGBA")
    alpha = rgba.getchannel("A")
    a_min, a_max = alpha.getextrema()
    has_transparency = a_max < 255 or a_min < 255

    if not has_transparency:
        # Opaque file: check for a white background to key out.
        rgb = rgba.convert("RGB")
        px = rgb.getdata()
        n = rgb.width * rgb.height
        white_frac = sum(1 for q in px if q[0] > 240 and q[1] > 240
                         and q[2] > 240) / n
        if white_frac > 0.70:
            # White-background export: key near-white to transparent, then
            # handled as a transparency case below (dark marks get inverted).
            data = [(r, g, b, 0 if r > 240 and g > 240 and b > 240 else 255)
                    for r, g, b, _ in rgba.getdata()]
            rgba.putdata(data)
            alpha = rgba.getchannel("A")
            has_transparency = True
        else:
            # Opaque non-white file (e.g. white-on-black RGB): use as-is.
            return _guard_logo(rgb, p)

    # Mark luminance from the visible pixels.
    lum = [0.299 * r + 0.587 * g + 0.114 * b
           for (r, g, b, a) in rgba.getdata() if a > 128]
    if not lum:
        print(f"[render] WARNING: logo pin {p} is fully transparent "
              f"— falling back to glyph")
        return None
    if sum(lum) / len(lum) < 80:
        # Dark mark on transparency: invert the colors, keep the alpha.
        inv = ImageOps.invert(rgba.convert("RGB"))
        rgba = Image.merge("RGBA", (*inv.split(), alpha))
    flat = Image.alpha_composite(
        Image.new("RGBA", rgba.size, (0, 0, 0, 255)), rgba).convert("RGB")
    return _guard_logo(flat, p)


def _guard_logo(rgb, p):
    """Reject white boxes and invisible marks. Returns rgb or None."""
    px = list(rgb.getdata())
    n = len(px)
    white_frac = sum(1 for q in px
                     if q[0] > 240 and q[1] > 240 and q[2] > 240) / n
    if white_frac > 0.95:
        print(f"[render] WARNING: logo pin {p} is a white box "
              f"({white_frac:.0%} near-white) — rejected, "
              f"falling back to glyph")
        return None
    dark_frac = sum(1 for q in px
                    if q[0] < 32 and q[1] < 32 and q[2] < 32) / n
    if dark_frac > 0.98:
        print(f"[render] WARNING: logo pin {p} is invisible on black "
              f"— rejected, falling back to glyph")
        return None
    return rgb


def frame_layout(src, W, H, out_path):
    """Terminal-era still layout (2026-10-09, rev 2026-10-09b).

    The frame background is ALWAYS black. Every still is fit *inside* the
    shot region (full width, y TOP_PAD..SHOT_REGION_BOTTOM, centered) over
    black — portrait shots get black pillars, landscapes get black above
    and below within the region. The bottom third stays black for the
    terminal captions, which sit at one fixed spot (top-middle of the
    bottom third) for the whole video. Returns the path ffmpeg should use.
    """
    # 2026-10-11b: stills centered at frame vertical middle (y=960),
    # not bottom-aligned — bottom-align pushed deep-dive shots off-center.
    TOP_PAD, REGION_BOTTOM = int(200 * H / 1920), int(1420 * H / 1920)
    im = Image.open(src).convert("RGB")
    iw, ih = im.size
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    rw, rh = W, REGION_BOTTOM - TOP_PAD
    s = min(rw / iw, rh / ih)
    fg = im.resize((max(1, int(iw * s)), max(1, int(ih * s))),
                   Image.LANCZOS)
    mid_y = int(960 * H / 1920)
    safe_bottom = int(1400 * H / 1920)  # 50px above captions — never touch
    y = mid_y - fg.height // 2
    if y + fg.height > safe_bottom:
        y = safe_bottom - fg.height
    canvas.paste(fg, ((rw - fg.width) // 2, y))
    canvas.save(out_path, quality=92)
    return str(out_path)


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    w, h, fps = CFG[mode]["width"], CFG[mode]["height"], CFG[mode]["fps"]
    preset, crf = CFG[mode]["preset"], CFG[mode]["crf"]

    visuals = json.loads((ROOT / "output" / "visuals.json").read_text())
    seg_dir = ROOT / "output" / "segments"
    seg_dir.mkdir(exist_ok=True)

    script = json.loads((ROOT / "output" / "script.json").read_text())
    words = json.loads((ROOT / "output" / "words.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    # Story numbering (shot-grammar rule 12): story_ids order defines 1..N.
    # Story hooks get a numbered pill at center-top third; every shot of a
    # story's deep-dive segment gets its number as a badge at middle-right
    # of the top third
    # (replacing the retired company-logo overlay).
    story_num = {str(sid): n + 1
                 for n, sid in enumerate(script.get("story_ids", []))}

    def seg_number(si):
        """1-based story number for a segment index, or None."""
        if si is None or si >= len(script["segments"]):
            return None
        return story_num.get(str(script["segments"][si].get("story_id") or ""))

    def number_badge(n, dest):
        """276x132 dark pill with a white bold number — the corner badge."""
        from PIL import Image, ImageDraw, ImageFont
        W_, H_ = 276, 132
        img = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, W_ - 1, H_ - 1], radius=30,
                            fill=(48, 48, 48, 235))  # 2026-10-12: was
        # (0,0,0,140) — invisible on black backgrounds, so badges rendered
        # as bare numbers. A lifted dark pill reads as a pill on black.
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 84)
        txt = f"#{n}"  # 2026-10-11: story numbers show as #1, #2, etc.
        bbox = d.textbbox((0, 0), txt, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((W_ - tw) / 2 - bbox[0], (H_ - th) / 2 - bbox[1]),
               txt, font=font, fill=(255, 255, 255, 255))
        img.save(dest)
        return str(dest)

    # Story-icon glyphs for the intro (2026-10-09): white line icons in the
    # terminal aesthetic. script.json story_icons maps story_id ->
    # "logo_<name>.png" (verified pin, for company stories) or "glyph:<name>".
    # 2026-10-11: the intro hooks show REAL PHOTOS of each story's key
    # person instead (script.json story_people -> "person_<name>.png");
    # logos/glyphs are fallback only. Person photos display at PERSON_H
    # (faces must read); logos keep LOGO_H. Laid side-by-side centered,
    # wrapping to 2 rows if too wide.
    ICON_S = 140  # glyph draw size (scaled to LOGO_H on load)
    LOGO_H, LOGO_GAP = 112, 28
    LOGO_MARGIN_X, LOGO_MAX_W = 60, 400
    # PERSON_H (2026-10-11): intro hook visuals are real photos of each
    # story's key person (not company logos) — faces need height to read,
    # so person photos display larger than logos did.
    PERSON_H = 240
    # LOGO_Y is DYNAMIC (2026-10-10): logos sit above the people photo with
    # a small gap — computed in intro_video from PEOPLE_IMG_Y.
    LOGO_GAP_ABOVE_PHOTO = 30
    PEOPLE_IMG_Y = 600   # top of the intro people portrait
    PEOPLE_IMG_W = 950   # fitted width (aspect kept)
    INTRO_TEXT_Y = 1450  # intro text top (aligned to caption zone)
    INTRO_FSIZE = 48     # intro text size (scaled down 2026-10-10)
    INTRO_LX = 60        # intro text left x (matches ASS captions)

    def draw_glyph(name):
        from PIL import Image, ImageDraw
        S = ICON_S
        WHITE = (255, 255, 255)
        im = Image.new("RGB", (S, S), (0, 0, 0))
        d = ImageDraw.Draw(im)
        if name == "bubble":        # social post
            d.rounded_rectangle([20, 25, 120, 95], radius=22,
                                outline=WHITE, width=10)
            d.polygon([(45, 95), (45, 120), (75, 95)], fill=WHITE)
        elif name == "chip":        # compute / AI hardware
            d.rounded_rectangle([40, 40, 100, 100], radius=8,
                                outline=WHITE, width=10)
            d.rectangle([58, 58, 82, 82], outline=WHITE, width=8)
            for x in (52, 70, 88):
                d.line([(x, 18), (x, 40)], fill=WHITE, width=8)
                d.line([(x, 100), (x, 122)], fill=WHITE, width=8)
                d.line([(18, x), (40, x)], fill=WHITE, width=8)
                d.line([(100, x), (122, x)], fill=WHITE, width=8)
        elif name == "scales":      # lawsuit / legal
            d.line([(70, 18), (70, 115)], fill=WHITE, width=9)
            d.line([(30, 38), (110, 38)], fill=WHITE, width=9)
            for cx in (30, 110):
                d.line([(cx, 38), (cx - 18, 78)], fill=WHITE, width=7)
                d.line([(cx, 38), (cx + 18, 78)], fill=WHITE, width=7)
                d.line([(cx - 18, 78), (cx + 18, 78)], fill=WHITE, width=7)
            d.line([(45, 115), (95, 115)], fill=WHITE, width=9)
        elif name == "chart-down":  # selloff / markets down
            d.line([(22, 22), (22, 118), (118, 118)], fill=WHITE, width=9)
            d.line([(30, 40), (55, 55), (75, 48), (105, 95)],
                   fill=WHITE, width=10, joint="curve")
            d.polygon([(105, 95), (88, 88), (96, 108)], fill=WHITE)
        elif name == "chart-up":    # markets up / growth
            d.line([(22, 22), (22, 118), (118, 118)], fill=WHITE, width=9)
            d.line([(30, 95), (55, 80), (75, 88), (105, 40)],
                   fill=WHITE, width=10, joint="curve")
            d.polygon([(105, 40), (88, 48), (96, 28)], fill=WHITE)
        elif name == "robot":       # AI model / agent
            d.rounded_rectangle([35, 45, 105, 115], radius=18,
                                outline=WHITE, width=10)
            d.line([(70, 45), (70, 25)], fill=WHITE, width=8)
            d.ellipse([62, 12, 78, 28], fill=WHITE)
            d.ellipse([50, 70, 62, 82], fill=WHITE)
            d.ellipse([78, 70, 90, 82], fill=WHITE)
        elif name == "newspaper":   # press / media
            d.rectangle([25, 30, 115, 110], outline=WHITE, width=9)
            d.line([(25, 52), (115, 52)], fill=WHITE, width=7)
            for yy in (68, 82, 96):
                d.line([(35, yy), (105, yy)], fill=WHITE, width=6)
        elif name == "bolt":        # breakthrough / speed
            d.polygon([(78, 15), (45, 80), (68, 80), (58, 125),
                       (95, 60), (70, 60)], fill=WHITE)
        else:
            return None
        return im

    def load_story_people():
        """5 intro visuals in story order, per script.json story_people.

        2026-10-11 (user): the headline hooks show REAL PHOTOS of each
        story's key person — not company logos. Per story_id:
          1. story_people[sid] -> "person_<name>.png" (eye-verified real
             photo pin). Must contain a detectable face (YuNet guard) —
             a person photo without a face is a bad pin.
          2. story_icons[sid] logo file -> transparency-aware loader.
          3. story_icons[sid] glyph -> drawn glyph.
          4. None (story gets no visual).
        Person photos keep native aspect at PERSON_H height (faces must
        read); logos/glyphs keep the old LOGO_H treatment. Returns a list
        of PIL Images (or None), pre-sized to display height."""
        people_specs = script.get("story_people", {}) or {}
        icon_specs = script.get("story_icons", {}) or {}

        def _size(ic, target_h):
            s = target_h / ic.height
            nw = int(ic.width * s)
            nh = target_h
            if nw > LOGO_MAX_W:
                s2 = LOGO_MAX_W / nw
                nw, nh = LOGO_MAX_W, int(nh * s2)
            if (nw, nh) != ic.size:
                ic = ic.resize((nw, nh), Image.LANCZOS)
            return ic

        def _has_face(path):
            try:
                from visuals import detect_face
                return detect_face(path) is not None
            except Exception as e:
                print(f"[render] face guard unavailable for {path}: {e}")
                return True  # fail open — worker eye-verification is primary

        out = []
        for sid in script.get("story_ids", []):
            sid = str(sid)
            person_ic = None
            pspec = people_specs.get(sid, "")
            if pspec:
                p = ROOT / "cache" / "verified" / pspec
                if p.exists():
                    if _has_face(p):
                        try:
                            person_ic = Image.open(p).convert("RGB")
                            person_ic = _size(person_ic, PERSON_H)
                        except Exception as e:
                            print(f"[render] WARNING: cannot open person "
                                  f"photo {p}: {e}")
                            person_ic = None
                    else:
                        print(f"[render] WARNING: person photo {p} has no "
                              f"detectable face — bad pin, falling back "
                              f"to logo/glyph")
                        person_ic = None
            # Company logo (stacked UNDER the person photo, 2026-10-11).
            logo_ic = None
            spec = icon_specs.get(sid, "")
            if spec.startswith("glyph:"):
                logo_ic = draw_glyph(spec[6:])
            elif spec:
                p = ROOT / "cache" / "verified" / spec
                if p.exists():
                    logo_ic = _load_intro_logo(p)
                    if logo_ic is None:
                        logo_ic = draw_glyph("newspaper")
            if logo_ic is not None:
                logo_ic = _size(logo_ic, LOGO_H)
            # Stack: person photo on top, logo below (12px gap). If no
            # person photo, show logo alone (old fallback behavior).
            # Intro uses logos-only (2026-10-11: user reverted the
            # person+logo stack from the intro — pairs belong in the
            # headline hooks, not the cold-open).
            out.append(logo_ic if logo_ic is not None else person_ic)
        return out

    def layout_logos(icons, y_top=None):
        """Position intro visuals: side-by-side, centered; wraps to 2 rows
        if the single row exceeds the available width. y_top defaults to
        the dynamic position above the people photo. Handles mixed heights
        (person photos at PERSON_H, logos/glyphs at LOGO_H) — each row is
        as tall as its tallest item, smaller items center vertically.
        Returns a list of (story_index, img, x, y). Fade order stays story
        order."""
        vis = [(k, ic) for k, ic in enumerate(icons or []) if ic is not None]
        if not vis:
            return []
        max_row_w = w - 2 * LOGO_MARGIN_X
        total_1row = (sum(ic.width for _, ic in vis)
                      + LOGO_GAP * (len(vis) - 1))
        if total_1row <= max_row_w:
            rows = [vis]
        else:
            # Two balanced rows (3+2 for five visuals).
            split = (len(vis) + 1) // 2
            rows = [vis[:split], vis[split:]]
            print(f"[render] intro visuals wrap to {len(rows)} rows "
                  f"(1-row width {total_1row}px > {max_row_w}px)")
        row_gap = 36
        row_hs = [max(ic.height for _, ic in row) for row in rows]
        if y_top is None:
            # Room for ALL rows above the people photo (2026-10-10 fix:
            # row 2 used to land under the portrait, which is pasted later).
            y_top = (PEOPLE_IMG_Y - sum(row_hs)
                     - (len(rows) - 1) * row_gap - LOGO_GAP_ABOVE_PHOTO)
        positions = []
        y = y_top
        for row, rh in zip(rows, row_hs):
            rw = (sum(ic.width for _, ic in row)
                  + LOGO_GAP * (len(row) - 1))
            x = (w - rw) // 2
            for k, ic in row:
                iy = y + (rh - ic.height) // 2
                positions.append((k, ic, int(x), int(iy)))
                x += ic.width + LOGO_GAP
            y += rh + row_gap
        return positions

    def intro_video(text: str, words, seg_dur: float, dest, icons=None):
        """Terminal intro (2026-10-09): the cold-open line types itself
        word by word in glowing green monospace on black — "> " prompts,
        block cursor — while 5 story visuals fade in side-by-side above the
        text, in story order. Since 2026-10-11 the visuals are REAL PHOTOS
        of each story's key person (not company logos). Synced to the
        narration's word timestamps.
        Time-based frames (not word-states) so the icon fades stay smooth.
        The layout is computed once so lines never reflow between frames."""
        from PIL import Image, ImageDraw, ImageFont
        W_, H_ = w, h
        GREEN = (57, 255, 20)      # neon green (2026-10-09)
        GLOW = (0, 100, 8)
        RED = (255, 70, 70)        # "BREAKING" kicker (2026-10-09)

        def _font(sz):
            try:
                return ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                    sz)
            except Exception:
                return ImageFont.load_default()

        parts = text.split(",", 1)
        kicker = parts[0].strip().upper()
        rest = parts[1].strip().upper() if len(parts) > 1 else ""
        # Token 0 is the kicker, alone on line 0; the rest wrap below.
        tokens = [kicker] + rest.split()
        meas = ImageDraw.Draw(Image.new("RGB", (W_, H_)))

        def _layout(fsize):
            f = _font(fsize)
            maxw = W_ - 2 * INTRO_LX - 30
            if meas.textlength("> " + kicker, font=f) > maxw:
                return None
            lines = [[0]]
            cur, cur_w = [], meas.textlength("> ", font=f)
            for j in range(1, len(tokens)):
                add = tokens[j] if not cur else " " + tokens[j]
                ww = meas.textlength(add, font=f)
                if cur_w + ww <= maxw:
                    cur.append(j)
                    cur_w += ww
                else:
                    lines.append(cur)
                    cur = [j]
                    cur_w = meas.textlength("> " + tokens[j], font=f)
            if cur:
                lines.append(cur)
            return lines

        fsize = INTRO_FSIZE
        lines = _layout(fsize)
        f = _font(fsize)
        lh = int(fsize * 1.35)
        prompt_w = meas.textlength("> ", font=f)
        y_top = INTRO_TEXT_Y
        # Token geometry, computed once (lines left-aligned at INTRO_LX).
        tok_pos = {}   # token idx -> (line idx, x of token start)
        for li, ln in enumerate(lines):
            x = INTRO_LX + prompt_w
            for j in ln:
                tok_pos[j] = (li, x)
                x += meas.textlength(tokens[j] + " ", font=f)

        def _text(d, xy, s, color=None):
            x, y = xy
            c = color or GREEN
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                d.text((x + dx, y + dy), s, font=f, fill=GLOW)
            d.text((x, y), s, font=f, fill=c)

        # Per-word timing, synced to the narration's own word timestamps.
        norm = lambda s_: re.sub(r"[^a-z0-9]", "", s_.lower())
        ok = (len(words) >= len(tokens) and
              all(norm(words[i]["word"]) == norm(tokens[i])
                  for i in range(len(tokens))))
        n = len(tokens)
        if ok and n:
            starts = [words[i]["start"] for i in range(n)]
            ends = [words[i]["end"] for i in range(n)]
        else:
            if n:
                print("[render] WARNING: intro word alignment mismatch, "
                      "using even spacing")
            starts = [seg_dur * (i + 1) / (n + 1) for i in range(n)]
            ends = [s + 0.25 for s in starts]

        # Time-based frames: logos fade in sequentially (story order);
        # text types LETTER-by-letter like the terminal captions (2026-10-09)
        # — each word's letters spread across its spoken duration.
        n_frames = max(1, int(seg_dur * fps))
        frame_dur = seg_dur / n_frames
        stagger = 0.3  # fast fade-in (2026-10-10): logos pop in quickly
        fade_dur = 0.3
        logo_positions = layout_logos(icons)
        # People portrait (2026-10-09): Pixar-style Trump/Altman/Huang with
        # story emotions, between logos and text.
        people_img = None
        try:
            _pp = Image.open(ROOT / "cache" / "verified" / "intro_people.png"
                             ).convert("RGB")
            _s = PEOPLE_IMG_W / _pp.width
            people_img = _pp.resize(
                (PEOPLE_IMG_W, int(_pp.height * _s)), Image.LANCZOS)
        except Exception:
            people_img = None

        def frame_at(t):
            img = Image.new("RGB", (W_, H_), (0, 0, 0))
            for k, ic, x, y in logo_positions:
                # 2026-10-11 motion upgrade (logo-animation: staggered
                # build-on): logos enter with easeOutCubic scale 0.85 -> 1.0
                # + fade, centered on their layout slot. Stagger stays 0.3s.
                p = max(0.0, min(1.0, (t - k * stagger) / fade_dur))
                if p > 0:
                    e = 1 - (1 - p) ** 3
                    s = 0.85 + 0.15 * e
                    w2 = max(1, int(ic.width * s))
                    h2 = max(1, int(ic.height * s))
                    lic = (ic.resize((w2, h2), Image.LANCZOS)
                           if s < 1.0 else ic)
                    px, py = x + (ic.width - w2) // 2, y + (ic.height - h2) // 2
                    black = Image.new("RGB", lic.size, (0, 0, 0))
                    img.paste(Image.blend(black, lic, e), (px, py))
            if people_img is not None:
                # Shown immediately, no fade (2026-10-10 user feedback).
                img.paste(people_img,
                          ((W_ - people_img.width) // 2, PEOPLE_IMG_Y))
            d = ImageDraw.Draw(img)
            # Letter-by-letter typing: each word's letters appear evenly
            # across its spoken [start, end]; the cursor follows the last
            # visible letter.
            def _vis_letters(j):
                if not n or t < starts[j]:
                    return 0
                span = max(0.05, ends[j] - starts[j])
                k = int((t - starts[j]) / span * len(tokens[j])) + 1
                return min(len(tokens[j]), max(0, k))
            vis_n = [_vis_letters(j) for j in range(n)]
            cur = -1
            for j in range(n):
                if vis_n[j] > 0:
                    cur = j
            # Only lines up to the one being typed exist yet.
            cur_line = tok_pos[cur][0] if cur >= 0 else 0
            for li, ln in enumerate(lines):
                if li > cur_line:
                    continue
                y = y_top + li * lh
                # "> " prompt is red on the BREAKING line (2026-10-10).
                _text(d, (INTRO_LX, y), "> ", RED if li == 0 else None)
                for j in ln:
                    if vis_n[j] > 0:
                        # Token 0 is the "BREAKING" kicker -> red (2026-10-09).
                        _text(d, (tok_pos[j][1], y), tokens[j][:vis_n[j]],
                              RED if j == 0 else None)
            if cur < 0:
                cli, cx = 0, INTRO_LX + prompt_w
            else:
                cli = tok_pos[cur][0]
                shown = tokens[cur][:vis_n[cur]]
                cx = tok_pos[cur][1] + meas.textlength(shown, font=f)
            cy = y_top + cli * lh + 6
            d.rectangle([cx, cy, cx + int(fsize * 0.55), cy + fsize],
                        fill=RED if cur == 0 else GREEN)
            return img

        fdir = seg_dir / "intro_frames"
        fdir.mkdir(exist_ok=True)
        for p in fdir.glob("f*.png"):
            p.unlink()
        lst = fdir / "frames.txt"
        with open(lst, "w") as fh:
            fh.write("ffconcat version 1.0\n")
            for k in range(n_frames):
                fp = fdir / f"f{k:04d}.png"
                frame_at(k * frame_dur).save(fp)
                fh.write(f"file '{fp}'\nduration {frame_dur:.4f}\n")
            fh.write(f"file '{fdir / f'f{n_frames-1:04d}.png'}'\n")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
             # NOTE: no fade filter here — fade misbehaves on concat-demuxer
             # timestamps (blacks out the first segment). The fade is applied
             # at the shot-encode step instead (clip branch, is_intro).
             "-vf", "format=yuv420p",
             "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-preset", "veryfast", "-crf", "18", str(dest)])
        print(f"[render] intro animation generated ({dest.name}, "
              f"{n_frames} frames, {len(logo_positions)} logos)")
        return str(dest)

    def youtube_card(dest):
        """Branding-hook card (2026-10-09, rev 2026-10-09b): the YouTube
        logo as the visual for the 'link in bio' section — official red
        play mark (verified pin) + white wordmark on a dark gradient. The
        follow CTA lives in the narration only (not on the card). Rendered
        at the shot-region size (1080x1220); frame_layout centers it in
        the top region over black like every other shot."""
        from PIL import Image, ImageDraw, ImageFont
        W_, H_ = w, 1220
        img = Image.new("RGB", (W_, H_), (8, 10, 16))
        d = ImageDraw.Draw(img)
        for yy in range(0, H_, 4):
            t = yy / H_
            d.line([(0, yy), (W_, yy)],
                   fill=(int(8 + 12 * t), int(10 + 14 * t), int(16 + 26 * t)))
        logo = Image.open(ROOT / "cache" / "verified" / "logo_youtube.png")
        lw = 400
        logo = logo.resize((lw, int(lw * logo.height / logo.width)),
                           Image.LANCZOS)
        img.paste(logo, ((W_ - logo.width) // 2, 300),
                  logo if logo.mode == "RGBA" else None)

        def _font(sz):
            try:
                return ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
            except Exception:
                return ImageFont.load_default()

        d.text((W_ // 2, 640), "YouTube", font=_font(110),
               fill=(245, 247, 255), anchor="mm")
        d.text((W_ // 2, 770), "LINK IN BIO", font=_font(60),
               fill=(255, 69, 58), anchor="mm")
        img.save(dest)
        print(f"[render] youtube card generated ({dest.name})")
        return str(dest)

    seg_files = []
    # Shot-region geometry (2026-10-11b): visuals centered at frame
    # vertical middle (y=960). Was bottom-aligned at y 1420 (pushed
    # deep-dives off-center). Intro and analytics untouched.
    TOP_PAD, REGION_H = 200, 1220
    _prev_badge_n = None  # 2026-10-11: badge fades in once per story,
    # then stays solid for remaining shots until next story.
    for v in visuals:
        i, dur = v["idx"], v["duration"]
        out = seg_dir / f"shot_{i:02d}.mp4"
        # Intro (2026-10-09): the cold-open hook gets a full-screen title
        # card in huge type instead of b-roll — its text IS the visual.
        # Branding hook ("link in bio"): the YouTube logo as its visual.
        is_intro = (v.get("segment") == 0 and v.get("seg_kind") == "hook")
        seg = script["segments"][v["segment"]] \
            if v.get("segment", 0) < len(script["segments"]) else {}
        is_branding = (v.get("seg_kind") == "hook"
                       and not seg.get("story_id")
                       and v.get("segment") != 0)
        if is_intro:
            # Animated word-by-word intro (2026-10-09) — regenerated every
            # run since the cold-open line is written fresh daily.
            anim = seg_dir / "intro_anim.mp4"
            seg0_end = timings[0]["start"] + timings[0]["duration"]
            iw = [ww for ww in words if ww["start"] < seg0_end]
            intro_video(script["segments"][0]["text"], iw, dur, anim,
                        load_story_people())
            v = dict(v, kind="clip", path=str(anim))
            print(f"[render] shot {i}: animated intro ({len(iw)} words)")
        elif is_branding:
            # Self-plug (2026-10-10): Pixar character montage (Trump/Altman/
            # Jensen doing their story beats) — NOT stock, NOT the old
            # firings clip. Fails LOUD if the clip is missing.
            clip = ROOT / "cache" / "generated" / "selfplug_pixar.mp4"
            if not clip.exists():
                raise FileNotFoundError(
                    f"[render] FATAL: self-plug clip missing: {clip}")
            v = dict(v, kind="clip", path=str(clip))
            print(f"[render] shot {i}: self-plug PIXAR clip ({clip.name})")
        # Analytical animations (2026-10-09): number-heavy shots get
        # terminal-style motion graphics instead of b-roll. Map is rebuilt
        # daily for the current script — stale indices play the WRONG
        # graphic (2026-10-10: genesis_pledges fired on the ICO shot).
        _analytics_map = {
            17: "analytics_broadcom_outlook.mp4",  # $115B AI chip outlook vs $42B Anthropic loan
        }
        if i in _analytics_map:
            ap = ROOT / "cache" / "generated" / _analytics_map[i]
            if ap.exists():
                v = dict(v, kind="clip", path=str(ap))
                print(f"[render] shot {i}: analytical animation "
                      f"({_analytics_map[i]})")
        # Badge at middle-right of the top third (rule 12): every shot of
        # a story's deep-dive segment carries the story number there.
        # Badge PNGs are generated once and reused across the shots.
        badge = None
        n = None
        if v.get("seg_kind") == "story":
            n = seg_number(v.get("segment"))
            if n:
                badge = seg_dir / f"badge_{n}.png"
                if not badge.exists():
                    number_badge(n, badge)
                badge = str(badge)
                print(f"[render] shot {i}: story-number badge {n} "
                      f"middle-right of top third")

        # Number badge: story identifier at top-right, VERTICALLY CENTERED
        # on the watermark (watermark at y=190, 34pt -> center ~212; badge
        # 132px tall -> y=146). 2026-10-11 safe-area fix (motion-skills
        # audit): badge right edge now sits at x=960, clear of TikTok's
        # ~120px right-rail UI zone (was W-300, intruding 96px into it).
        # The badge PNG already carries its dark pill, so it composites
        # directly.
        def with_badge(base_vf, main_args, first_of_story=True):
            # 2026-10-11 motion upgrade (animation-principles): the badge
            # enters with a 0.4s ease-out grow (0.92 -> 1.0) + alpha fade —
            # enters use ease-out, 300-500ms. eval=frame so the scale
            # animates per frame; t-based (not frame-count) so it holds
            # regardless of input framerate. After 0.4s it holds static.
            # 2026-10-11b: only the first shot of each story fades in;
            # subsequent shots of the same story show it solid.
            _be = "(1-pow(1-min(t,0.4)/0.4,3))"
            if first_of_story:
                bvf = (f"{base_vf}[base];"
                       f"[1:v]format=rgba,"
                       f"scale=w='276*(0.92+0.08*{_be})'"
                       f":h='132*(0.92+0.08*{_be})':eval=frame,"
                       f"fade=t=in:st=0:d=0.4:alpha=1[bg];"
                       f"[base][bg]overlay=W-336:146")  # right edge at 1020
            else:
                bvf = (f"{base_vf}[base];"
                       f"[1:v]format=rgba,scale=276:132[bg];"
                       f"[base][bg]overlay=W-336:146")  # right edge at 1020
            return (["ffmpeg", "-y"] + main_args +
                    ["-loop", "1", "-i", badge,
                     "-t", f"{dur:.2f}", "-filter_complex", bvf])
        if v["kind"] == "clip":
            if is_intro:
                # Full-frame terminal intro (already 1080x1920 black).
                vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                      f"crop={w}:{h},fps={fps},setsar=1")
                # Fade-in for the animated intro (applied here, not in
                # intro_video — fade misbehaves on concat-demuxer timestamps).
                vf += ",fade=t=in:st=0:d=0.8"
            else:
                # Stock clips fit inside the shot region over black —
                # background is always black; no Ken Burns on clips.
                # Vertically CENTERED in the region (2026-10-09 fix: the old
                # pad pinned clips at y=TOP_PAD, leaving them floating high
                # with black below).
                # Analytical animations (2026-10-10): MUST sit below the
                # watermark/badge (badge bottom y=278) — pad y=290, no overlap
                # with badge, watermark, or captions.
                _is_analytics = "analytics_" in v["path"]
                _pad_y = ("290" if _is_analytics
                            else r"min(960-ih/2\,1400-ih)")  # never touch captions
                vf = (f"format=rgb24,"
                      f"scale={w}:{REGION_H}:force_original_aspect_ratio=decrease,"
                      f"pad={w}:{h}:(ow-iw)/2:{_pad_y}:0x000000,"
                      f"fps={fps},setsar=1")
            # Analytical/self-plug clips (2026-10-10): play ONCE then HOLD the
            # last frame — never loop (the loop restart was the ugly cut at
            # 1:33). Stock clips still loop to fill. tpad runs in RGB (before
            # the yuv420p conversion) to avoid chroma tint on pure black.
            _no_loop = ("analytics_" in v["path"] or "selfplug_" in v["path"])
            if _no_loop:
                base = ["-i", v["path"]]
                # 2026-10-12: hold the last frame to fill the planned shot
                # duration. ffmpeg's -t is a CAP, not a pad — a clip shorter
                # than its shot (self-plug was 5.69s vs 7.02s planned) used
                # to end early, shifting EVERY later shot early so story
                # visuals changed before the narrator finished the prior
                # story. tpad runs in RGB (before yuv420p) to avoid chroma
                # tint on pure black.
                try:
                    cprobe = subprocess.run(
                        ["ffprobe", "-v", "quiet", "-show_entries",
                         "format=duration", "-of", "csv=p=0", v["path"]],
                        capture_output=True, text=True, check=True)
                    clip_dur = float(cprobe.stdout.strip())
                except Exception:
                    clip_dur = dur
                hold = dur - clip_dur
                if hold > 0.02:
                    vf += (f",tpad=stop_mode=clone:"
                           f"stop_duration={hold:.3f}")
                    print(f"[render] shot {i}: holding last frame "
                          f"+{hold:.2f}s (clip {clip_dur:.2f}s < "
                          f"planned {dur:.2f}s)")
            else:
                base = ["-stream_loop", "-1", "-i", v["path"]]
            _first = (n != _prev_badge_n)
            cmd = (with_badge(f"[0:v]{vf}", base, _first) if badge else
                   ["ffmpeg", "-y"] + base +
                   ["-t", f"{dur:.2f}", "-vf", vf])
            run(cmd + ["-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                       "-preset", preset,
                       "-crf", "23", str(out)])
        else:  # photo / title card -> terminal layout, then elastic zoom-out
            src = frame_layout(v["path"], w * 2, h * 2,
                               seg_dir / f"shot_{i:02d}_bg.jpg")
            frames = max(1, int(dur * fps))
            # Elastic zoom-OUT only, QUICK (2026-10-09): the zoom completes
            # in the first ~1.5s with one snappy elastic overshoot, then
            # holds static at exactly 1.0 — no more slow full-shot drift.
            # Document shots (articles, tables, posts): dense text must stay
            # legible — start the zoom at 1.05 instead of 1.12.
            zmax = 1.05 if v.get("doc") else 1.12
            zf = min(frames, int(1.5 * fps))
            z = (f"if(lt(on,{zf}),"
                 f"1+{zmax - 1:.3f}*pow(1-on/{zf},2)"
                 f"*(1+0.45*sin(6.283*on/{zf})*(1-on/{zf}))"
                 f",1)")
            # Center-crop to 9:16 BEFORE zoompan: zoompan stretches its zoom
            # window to the output size, so wide photos came out squeezed.
            # (frame_layout already made every still exactly 9:16, so this
            # crop is a no-op and the whole image stays visible.)
            vf = (f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
                  f"crop={w*2}:{h*2},"
                  f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
                  f"y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps={fps},setsar=1")
            if is_branding:
                # Transition in: fade up from black over the first 0.8s on
                # top of the slow Ken Burns push. (The animated intro bakes
                # its own fade in.)
                vf += ",fade=t=in:st=0:d=0.8"
            base = ["-loop", "1", "-framerate", str(fps), "-i", src]
            _first = (n != _prev_badge_n)
            cmd = (with_badge(f"[0:v]{vf}", base, _first) if badge else
                   ["ffmpeg", "-y"] + base + ["-vf", vf])
            # 2026-10-12: BT.709 tagging — prevents chroma shift that
            # tints dark backgrounds green (same root cause as analytics).
            run(cmd + ["-t", f"{dur:.2f}", "-frames:v", str(frames), "-an",
                       "-c:v", "libx264", "-pix_fmt", "yuv420p",
                       "-colorspace", "bt709", "-color_primaries", "bt709",
                       "-color_trc", "bt709", "-color_range", "tv",
                       "-preset", preset, "-crf", "23",
                       str(out)])
        _prev_badge_n = n if badge else None
        seg_files.append(out)

    lst = ROOT / "output" / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in seg_files))
    vcat = ROOT / "output" / "video_concat.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(vcat)])

    narration = ROOT / "output" / "narration_full.wav"
    captions = ROOT / "output" / "captions.ass"
    music_dir = ROOT / "assets" / "music"
    tracks = sorted(music_dir.glob("*.mp3")) if music_dir.exists() else []
    music = random.choice(tracks) if tracks else None

    inputs = ["-i", str(vcat), "-i", str(narration)]
    if music:
        inputs += ["-i", str(music)]
        # music bed at low constant volume under the voiceover, then loudnorm
        # the whole mix to broadcast-ish levels.
        afilter = ("[2:a]volume=0.12,aloop=loop=-1:size=2147483647[bg];"
                   "[1:a][bg]amix=inputs=2:duration=first:dropout_transition=0,"
                   "loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
        amap = "[aout]"
    else:
        afilter = "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
        amap = "[aout]"

    final = ROOT / "output" / f"ainews_{mode}.mp4"
    # Never cut the speaker: frame rounding can leave the shot plan a hair
    # shorter than the narration. Pad the video out to the narration length
    # instead of letting -shortest truncate the audio.
    # NOTE (2026-10-11, root-cause fix for "captions cut off at the end"):
    # tpad MUST come before every ass subtitle burn. The old order burned
    # subtitles onto the short video and padded after, which froze the last
    # frame AND silently dropped every subtitle past the unpadded duration.
    # Padding first gives the subtitle renderer frames for the full timeline.
    vdur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(vcat)],
        capture_output=True, text=True).stdout.strip() or 0)
    ndur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(narration)],
        capture_output=True, text=True).stdout.strip() or 0)
    pad = max(0.0, ndur - vdur)
    vf_parts = []
    if pad > 0.02:
        vf_parts.append(f"tpad=stop_mode=clone:stop_duration={pad:.3f}")
        print(f"[render] padding video {pad:.2f}s to narration length")
    # Emphasis pills: 2-4 word punch labels, white bold text on a black box,
    # centered mid-frame (never fights the terminal captions below).
    vf_parts.append(f"ass={captions}")
    # Watermark (2026-10-10): "@leos.logos" at 50%, positioned above logos
    # (y=190), left-aligned with text.
    vf_parts.append(
        "drawtext=text='@leos.logos':fontfile=/usr/share/fonts/truetype/"
        "dejavu/DejaVuSans-Bold.ttf:x=60:y=190:fontsize=34:"
        "fontcolor=white@0.5")
    # Emphasis pills as ASS events (not drawtext): they fade in right before
    # the emphasized words are spoken, and sit away from faces.
    # (script.json, words.json, timings.json already loaded at top of main
    # for story numbering and the animated intro.)
    def _norm(w):
        return re.sub(r"[^a-z0-9]", "", w.lower())

    def _ts(sec):
        sec = max(0.0, sec)
        h_, rem = divmod(sec, 3600)
        m_, s_ = divmod(rem, 60)
        return f"{int(h_)}:{int(m_):02d}:{s_:05.2f}"

    def find_phrase(seg_words, phrase):
        """(start, end) of the emphasis phrase in the whisper word stream.
        Requires CONSECUTIVE words — a subsequence spread across the
        segment would pin the pill up for 20+ seconds."""
        want = [_norm(w) for w in phrase.split()]
        want = [w_ for w_ in want if w_]
        if not want or not seg_words:
            return None
        have = [_norm(w_["word"]) for w_ in seg_words]
        for s_ in range(len(have) - len(want) + 1):
            if have[s_:s_ + len(want)] == want:
                return seg_words[s_]["start"], seg_words[s_ + len(want) - 1]["end"]
        return None

    def find_word(seg_words, word):
        """First occurrence of a single word."""
        w = _norm(word)
        for sw in seg_words:
            if _norm(sw["word"]) == w:
                return sw["start"], sw["end"]
        return None

    emph_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Emphasis,Arial,76,&H00FFFFFF,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,8,0,5,60,60,60,1
Style: HookNum,Arial,132,&H00FFFFFF,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,14,0,5,60,60,133,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    emph_events = []
    # Overlay geometry sidecar for QA safe-area checks (2026-10-11,
    # motion-skills audit): every burned-in overlay's rect/anchor, so qa.py
    # can verify nothing sits under TikTok's UI zones. Single source of
    # truth — these are the same constants used to place the overlays.
    overlay_geoms = [
        {"name": "story_badge", "rect": [w - 396, 146, w - 396 + 276, 278]},
        {"name": "watermark", "rect": [60, 190, 300, 228]},
        {"name": "hook_num_pill",
         # single 132pt digit centered on the badge (badge center x =
         # w-396+138 = w-258): ~80px wide, ~140px tall
         "rect": [w - 258 - 40, 212 - 70, w - 258 + 40, 212 + 70]},
        {"name": "captions", "anchor": [60, 1450]},
    ]
    # Hook pill x = badge center x, so the number never jumps between the
    # hooks and the deep-dives (2026-10-11: the safe-area move shifted the
    # badge left but the pill stayed behind — root cause of the jump).
    pill_x = w - 198  # 2026-10-11: matches badge center (W-336+138)
    story_ids = {str(sid).lower().replace("-", " ").replace("_", " ")
                 for sid in script.get("story_ids", [])}
    for si, seg in enumerate(script["segments"]):
        # Rule 12: story hooks get a numbered pill (1..5) at top-right —
        # matching the story-number badge position. The number is the thread
        # linking hook to story. It replaces any punch label on hooks;
        # story segments keep theirs.
        n = story_num.get(str(seg.get("story_id") or ""))
        if seg.get("kind") == "hook" and n and si < len(timings):
            tm = timings[si]
            seg_start, seg_end = tm["start"], tm["start"] + tm["duration"]
            estart = seg_start + 0.15
            eend = max(estart + 0.5, seg_end - 0.15)
            emph_events.append(
                f"Dialogue: 0,{_ts(estart)},{_ts(eend)},HookNum,,0,0,0,,"
                f"{{\\fad(300,250)\\pos({pill_x},212)}}#{n}")
            print(f"[render] hook {si}: numbered pill {n} at top-right")
            continue
        emph = (seg.get("emphasis") or "").strip()
        # Guard: emphasis must be a human punch label ("ROGUE AGENTS",
        # "FLASH-LITE ONLY"), never a leaked slug/ID ("ROGUE-HOOK1").
        # Slugs betray themselves with -HOOK/-SEG/-SHOT + digits, or by
        # matching a story_id; legit labels may hyphenate product names.
        slug_like = ("_" in emph
                     or re.search(r"-(hook|seg|segment|shot)\d*\b", emph, re.I)
                     or emph.lower() in story_ids)
        if emph and slug_like:
            print(f"[render] WARNING: dropping slug-like emphasis "
                  f"'{emph}' on segment {si}")
            emph = ""
        if not emph or si >= len(timings):
            continue
        tm = timings[si]
        seg_start, seg_end = tm["start"], tm["start"] + tm["duration"]
        seg_words = [w_ for w_ in words
                     if w_["start"] >= seg_start - 0.05 and w_["start"] < seg_end]
        m = find_phrase(seg_words, emph)
        if m:
            # Full phrase found back-to-back: pill hugs the spoken words.
            w0, w1 = m
            estart, eend = max(seg_start, w0 - 0.35), min(seg_end, w1 + 0.8)
        else:
            # Phrase not back-to-back in the transcript: anchor a short
            # pill on its first word instead of spanning the segment.
            first = emph.split()[0]
            wm = find_word(seg_words, first)
            if wm:
                estart = max(seg_start, wm[0] - 0.35)
            else:
                estart = seg_start + 0.3
            eend = estart + 2.5
        eend = min(eend, seg_end, estart + 4.0)  # pills stay punchy
        # Dynamic placement, snapped to third-centers: face in the top
        # half -> middle-center third (960); face in the middle or lower
        # -> center-top third (320); no face -> middle-center third.
        # A little overlap is fine; side placement stays available.
        face_xy = None
        for v in visuals:
            if (v.get("segment") == si and v.get("person")
                    and v.get("face_xy")
                    and not (v["start"] + v["duration"] <= estart
                             or v["start"] >= eend)):
                face_xy = v["face_xy"]
                break
        y = h // 6 if (face_xy and face_xy[1] >= 0.5) else h // 2
        safe = emph.replace("{", "\\{").replace("}", "\\}")
        emph_events.append(
            f"Dialogue: 0,{_ts(estart)},{_ts(eend)},Emphasis,,0,0,0,,"
            f"{{\\fad(300,250)\\pos(540,{y})}}{safe}")
        overlay_geoms.append({"name": f"emphasis_pill_seg{si}",
                              "anchor": [540, y]})
    if emph_events:
        epath = ROOT / "output" / "emphasis.ass"
        epath.write_text(emph_header + "\n".join(emph_events) + "\n")
        vf_parts.append(f"ass={epath}")
        print(f"[render] {len(emph_events)} emphasis pills (timed + face-aware)")
    run(["ffmpeg", "-y", *inputs,
         "-filter_complex", afilter,
         "-vf", ",".join(vf_parts),
         "-map", "0:v", "-map", amap,
         "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-level", "4.0",
         "-preset", preset, "-crf", str(crf),
         "-r", str(fps), "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
         "-shortest", "-movflags", "+faststart", str(final)])
    print(f"[render] done -> {final}")
    # Overlay geometry sidecar for QA safe-area checks.
    (ROOT / "output" / "overlays.json").write_text(json.dumps(
        {"width": w, "height": h, "overlays": overlay_geoms}, indent=1))


if __name__ == "__main__":
    main()
