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
        # (2026-10-13: normalize the inverted white to 85% — a raw
        # inversion glares pure-white against native white logos. User:
        # "make an effort to always find white logo and make background
        # black" — inverted marks should read as white, not glare.)
        inv = ImageOps.invert(rgba.convert("RGB")).point(lambda q: int(q * 0.85))
        rgba = Image.merge("RGBA", (*inv.split(), alpha))
    flat = Image.alpha_composite(
        Image.new("RGBA", rgba.size, (0, 0, 0, 255)), rgba).convert("RGB")
    return _guard_logo(flat, p)


def _autocrop_logo(rgb, margin=6):
    """Crop dead padding around a logo mark (2026-10-19, user: the Tesla
    logo rendered tiny in the intro). The pin was a 980x980 file whose
    mark occupied only a 711x213 middle band — scaling the padded file
    to LOGO_H shrank the mark to ~24px tall. Cropping to the content
    bounding box first means every logo renders at full mark size,
    however padded the source file is."""
    mask = rgb.convert("L").point(lambda v: 255 if v > 24 else 0)
    bbox = mask.getbbox()
    if not bbox:
        return rgb
    x0, y0, x1, y1 = bbox
    x0 = max(0, x0 - margin)
    y0 = max(0, y0 - margin)
    x1 = min(rgb.width, x1 + margin)
    y1 = min(rgb.height, y1 + margin)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return rgb
    return rgb.crop((x0, y0, x1, y1))


def _guard_logo(rgb, p):
    """Autocrop padding, then reject white boxes and invisible marks.
    Returns the cropped rgb or None.

    The invisible-content check runs on the UNcropped file: <2% non-black
    content means there is no usable mark no matter how tight the crop —
    without this, a near-empty file would crop to a speck and scale into
    a giant blurry blob instead of falling back to the glyph.
    """
    px = list(rgb.getdata())
    n = len(px)
    dark_frac = sum(1 for q in px
                    if q[0] < 32 and q[1] < 32 and q[2] < 32) / n
    if dark_frac > 0.98:
        print(f"[render] WARNING: logo pin {p} is invisible on black "
              f"— rejected, falling back to glyph")
        return None
    rgb = _autocrop_logo(rgb)
    px = list(rgb.getdata())
    n = len(px)
    white_frac = sum(1 for q in px
                     if q[0] > 240 and q[1] > 240 and q[2] > 240) / n
    if white_frac > 0.95:
        print(f"[render] WARNING: logo pin {p} is a white box "
              f"({white_frac:.0%} near-white) — rejected, "
              f"falling back to glyph")
        return None
    return rgb


def frame_layout(src, W, H, out_path, landscape=False, max_w=None,
                 doc=False, person=False):
    """Still layout (2026-10-09, rev 2026-10-23 portrait-fill).

    2026-10-23 (user): prioritise shots that FILL the 9:16 frame. A still
    whose aspect is close enough to 9:16 that a centre cover-crop loses
    <=30% of the frame is cover-cropped to the full frame — no black
    pillars, no black bars. Anything else gets a BLURRED background made
    from its own colours: the image scaled to cover the frame, heavily
    blurred and darkened, with the sharp image fit inside the visual zone
    (y 0..1400, above the caption fade) on top of it.
    Document shots (articles, tables, posts) NEVER cover-crop — a cover
    crop would slice headline text, which the 2026-10-20 vision-crop
    standard forbids. They always take the fit + blurred-background
    path, darkened harder so the text foreground still pops.
    The caption zone itself is handled in Pass 2 (a pure-black gradient
    overlay), so the blurred background never fights the captions.
    Returns the path ffmpeg should use.
    """
    from PIL import ImageEnhance, ImageFilter
    im = Image.open(src).convert("RGB")
    iw, ih = im.size
    if landscape:
        canvas = Image.new("RGB", (W, H), (0, 0, 0))
        s = min(W / iw, H / ih)
        if max_w:
            s = min(s, max_w / iw)
        fg = im.resize((max(1, int(iw * s)), max(1, int(ih * s))),
                       Image.LANCZOS)
        canvas.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
        canvas.save(out_path, quality=92)
        return str(out_path)
    target_aspect = W / H
    src_aspect = iw / ih
    if src_aspect >= target_aspect:
        cover_loss = 1.0 - target_aspect / src_aspect
    else:
        cover_loss = 1.0 - src_aspect / target_aspect
    # 2026-10-23 (user review fix): a PERSON photo must actually fill
    # the 9:16 frame, not sit as a strip with blurred background — a
    # centre crop to 9:16 centred on the detected face keeps the face
    # whole (crop width is checked against the face box) even when the
    # centre-crop loss is >30%. Non-person shots keep the old rule.
    _face_crop = None
    if person and not doc:
        try:
            import cv2
            _model = ROOT / "cache" / "models" / "face_yunet.onnx"
            if _model.exists():
                _img = cv2.imread(str(src))
                if _img is not None:
                    _ih, _iw = _img.shape[:2]
                    _det = cv2.FaceDetectorYN_create(
                        str(_model), "", (_iw, _ih), 0.5, 0.3, 5000)
                    _, _faces = _det.detect(_img)
                    if _faces is not None and len(_faces):
                        _f = max(_faces, key=lambda f: f[2] * f[3])
                        _fcx, _fcy = _f[0] + _f[2] / 2, _f[1] + _f[3] / 2
                        _fw, _fh = _f[2], _f[3]
                        if src_aspect >= target_aspect:
                            _cw = int(ih * target_aspect)
                            if _fw < _cw:
                                _x0 = int(min(max(_fcx - _cw / 2, 0), iw - _cw))
                                _face_crop = (_x0, 0, _x0 + _cw, ih)
                        else:
                            _ch = int(iw / target_aspect)
                            if _fh < _ch:
                                _y0 = int(min(max(_fcy - _ch / 2, 0), ih - _ch))
                                _face_crop = (0, _y0, iw, _y0 + _ch)
        except Exception as e:
            print(f"[render] face-crop skipped ({e})")
    if _face_crop is not None:
        crop = im.crop(_face_crop)
        out = crop.resize((W, H), Image.LANCZOS)
        out.save(out_path, quality=92)
        return str(out_path)
    if not doc and cover_loss <= 0.30:
        # Full-bleed cover: centre-crop to 9:16, resize to the frame.
        if src_aspect >= target_aspect:
            cw = int(ih * target_aspect)
            x0 = (iw - cw) // 2
            crop = im.crop((x0, 0, x0 + cw, ih))
        else:
            ch = int(iw / target_aspect)
            y0 = (ih - ch) // 2
            crop = im.crop((0, y0, iw, y0 + ch))
        out = crop.resize((W, H), Image.LANCZOS)
        out.save(out_path, quality=92)
        return str(out_path)
    # Blur-pad path: blurred cover background + sharp fit foreground.
    bg = im.copy()
    s_bg = max(W / iw, H / ih)
    bg = bg.resize((max(1, int(iw * s_bg)), max(1, int(ih * s_bg))),
                   Image.LANCZOS)
    bx = (bg.width - W) // 2
    by = (bg.height - H) // 2
    bg = bg.crop((bx, by, bx + W, by + H))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=max(20, W // 27)))
    bg = ImageEnhance.Brightness(bg).enhance(0.45 if doc else 0.70)
    # Foreground fits the visual zone only: full width, y 0..1400
    # (in 1920 coords), so it never sits under the caption fade.
    box_w, box_h = W, int(1400 * H / 1920)
    s = min(box_w / iw, box_h / ih)
    fg = im.resize((max(1, int(iw * s)), max(1, int(ih * s))),
                   Image.LANCZOS)
    bg.paste(fg, ((W - fg.width) // 2, (box_h - fg.height) // 2))
    bg.save(out_path, quality=92)
    return str(out_path)


def caption_gradient_png(dest, W=1080):
    """Pure-black caption area with a fading (not solid) top edge
    (2026-10-23, user). Returns a 1080x540 RGBA PNG meant to be overlaid
    at y=1380: alpha ramps 0 -> 255 over the first 70px with a smoothstep
    (so the edge reads as a soft blur, never a hard line), then stays
    solid black to the bottom of the frame (y=1920). Captions start at
    y=1450, i.e. just below the fade, on pure black."""
    from PIL import Image
    fade, total_h = 70, 1920 - 1380
    img = Image.new("RGBA", (W, total_h), (0, 0, 0, 255))
    px = img.load()
    for y in range(fade):
        t = y / fade
        a = int(255 * (t * t * (3 - 2 * t)))
        for x in range(W):
            px[x, y] = (0, 0, 0, a)
    img.save(dest)
    return str(dest)


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    w, h, fps = CFG[mode]["width"], CFG[mode]["height"], CFG[mode]["fps"]
    preset, crf = CFG[mode]["preset"], CFG[mode]["crf"]
    # Landscape mode (2026-10-13): 16:9 variant of the pipeline. Story
    # deep-dives split the frame — left third is a live terminal panel
    # typing the narration (this IS the caption track in landscape),
    # right two-thirds plays the visual. Intro/hooks/branding stay
    # full-frame. The 9:16 path below is untouched by LANDSCAPE branches.
    LANDSCAPE = (mode == "landscape")
    PANEL_W = 640 if LANDSCAPE else 0   # terminal panel width (left third)
    VIS_X = 640 if LANDSCAPE else 0     # visual region left edge
    VIS_W = (w - VIS_X) if LANDSCAPE else w  # visual region width

    visuals = json.loads((ROOT / "output" / "visuals.json").read_text())
    seg_dir = ROOT / "output" / "segments"
    seg_dir.mkdir(exist_ok=True)

    script = json.loads((ROOT / "output" / "script.json").read_text())
    words = json.loads((ROOT / "output" / "words.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    # Story numbering (shot-grammar rule 12): story_ids order defines 1..N.
    # 2026-10-23 (user): hooks and deep-dives carry the SAME number pill —
    # one PNG, one position, format "n/5" (138x66, centred on the old pill centre). Hooks used to get a separate
    # ASS text pill (#n, tight black box) while stories got a PNG badge
    # (#n, rounded dark pill) — different look, different text. Both now
    # get this badge, composited in the segment stage, centred at (W-198, 212).
    story_num = {str(sid): n + 1
                 for n, sid in enumerate(script.get("story_ids", []))}
    story_total = len(script.get("story_ids", [])) or 5

    def seg_number(si):
        """1-based story number for a segment index, or None."""
        if si is None or si >= len(script["segments"]):
            return None
        return story_num.get(str(script["segments"][si].get("story_id") or ""))

    def number_badge(n, dest, total=None):
        """138x66 rounded-rectangle pill, dark 50% transparent, with a
        CLEAN blur edge — the one number pill used by both hooks and
        story deep-dives, format "n/total".
        2026-10-23 (user: half as small, 50% transparent, clean blur):
        the pill rect is half the old 276x132, background alpha 128.
        Blur-root-cause fix: the old pill blurred a mask that filled the
        whole PNG, so its straight edges sat exactly on the image
        boundary — alpha jumped 0 -> 255 in 1px at the sides, and only
        the rounded corners looked soft. The new PNG carries a 24px
        transparent margin around the rect, and the mask is blurred
        (radius 14) INTO that margin, so alpha fades 128 -> 0 over
        ~30px before the canvas edge and the composited edge is soft
        all the way round, not just at the corners."""
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        total = total or story_total
        W_, H_, M = 138, 66, 24  # pill rect, plus transparent margin
        CW, CH = W_ + 2 * M, H_ + 2 * M
        mask = Image.new("L", (CW, CH), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle([M, M, M + W_ - 1, M + H_ - 1], radius=18,
                             fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(14))
        img = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        dark = Image.new("RGBA", (CW, CH), (24, 24, 24, 128))
        img.paste(dark, (0, 0), mask)
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        txt = f"{n}/{total}"
        bbox = d.textbbox((0, 0), txt, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((CW - tw) / 2 - bbox[0], (CH - th) / 2 - bbox[1]),
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
    PERSON_H = 200 if LANDSCAPE else 240
    # LOGO_Y is DYNAMIC (2026-10-10): logos sit above the people photo with
    # a small gap — computed in intro_video from PEOPLE_IMG_Y.
    LOGO_GAP_ABOVE_PHOTO = 30
    if LANDSCAPE:
        # Landscape intro geometry (2026-10-13): the people row, portrait,
        # and text stack to fit 1080px — portrait is 3:2 so it can't
        # dominate like in 9:16.
        PEOPLE_IMG_Y = 270   # top of the intro people portrait
        PEOPLE_IMG_W = 800   # fitted width (aspect kept, 3:2 -> 533 tall)
        INTRO_TEXT_Y = 840   # intro text top (clear of the portrait)
        INTRO_FSIZE = 54     # intro text size
        INTRO_LX = 80        # intro text left x
    else:
        PEOPLE_IMG_Y = 600   # top of the intro people portrait
        PEOPLE_IMG_W = 1020  # fitted width, aspect kept (2026-10-17: bigger
                             # per user — near full-bleed with 30px margins)
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
        RED = (255, 30, 30)          # "BREAKING" kicker (2026-10-09;
                                     # 2026-10-18: true neon solid red —
                                     # the old (255,70,70) read as orange)

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
        logo_positions = None  # laid out after the portrait (needs its height)
        # People portrait (2026-10-09): Pixar-style Trump/Altman/Huang with
        # story emotions, between logos and text.
        people_img = None
        try:
            _pp = Image.open(ROOT / "cache" / "verified" / "intro_people.png"
                             ).convert("RGB")
        except Exception:
            _pp = None
        if _pp is not None:
            # 2026-10-23 LAYOUT GUARD (user: portrait original, supersedes
            # the 2026-10-16 landscape guard): the intro portrait MUST be
            # a GROUP composition (one character per story, up to 5) in
            # PORTRAIT (aspect <= 0.85) — the old landscape guard would
            # now fail the correct pin. A single-character portrait is
            # still a fail. Portrait pins are fitted by height here so
            # they do not cover half the frame (the old landscape failure
            # mode, in reverse).
            # (Deliberately OUTSIDE the try above — this error must NOT be
            # swallowed into a silent None.)
            _aspect = _pp.width / _pp.height
            if _aspect > 0.85:
                raise ValueError(
                    f"[render] FATAL: intro_people.png is {_pp.width}x"
                    f"{_pp.height} (aspect {_aspect:.2f}) — must be a "
                    f"PORTRAIT group portrait (aspect <= 0.85), one Pixar "
                    f"character per story. Regenerate it; refusing to "
                    f"render a broken intro layout.")
            _target_h = 800
            _s = _target_h / _pp.height
            people_img = _pp.resize(
                (int(_pp.width * _s), _target_h), Image.LANCZOS)
            # 2026-10-17 CENTERING (user: the group portrait should be
            # bigger and centered): center it on the frame's vertical
            # middle. Logos are laid out after this, so they sit above
            # wherever the portrait lands.
            PEOPLE_IMG_Y = 960 - people_img.height // 2
        logo_positions = layout_logos(icons)

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

    def terminal_panel(seg_idx, dest):
        """Landscape-only (2026-10-13): the left-third terminal panel.
        The segment's narration types itself word-by-word in glowing
        green mono, synced to the TTS word timestamps — this IS the
        caption track in landscape, so no ASS captions are burned.
        One panel clip is rendered per story segment; shots slice their
        time range out of it, keeping typing in sync automatically."""
        from PIL import Image, ImageDraw, ImageFont
        PW, PH = PANEL_W, h
        GREEN = (57, 255, 20)
        GLOW = (0, 100, 8)
        try:
            f_body = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                26)
            f_head = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                30)
        except Exception:
            f_body = f_head = ImageFont.load_default()
        tm = timings[seg_idx]
        seg_start, seg_dur = tm["start"], tm["duration"]
        seg = script["segments"][seg_idx]
        n = story_num.get(str(seg.get("story_id") or "")) or 0
        sid = str(seg.get("story_id") or "").upper()
        header = f"> #{n} {sid}" if n else "> DIGEST"
        seg_words = [ww for ww in words
                     if seg_start - 0.05 <= ww["start"] < seg_start + seg_dur]
        # Word-wrap once — layout never reflows between frames.
        # (2026-10-13 fix: the leading space of each word must be part of
        # its x position — the first version measured the space for
        # wrapping but dropped it when drawing, jamming words together.)
        meas = ImageDraw.Draw(Image.new("RGB", (PW, PH)))
        maxw = PW - 80
        lines, wstarts = [], []
        cur, x = [], 40
        for wd in seg_words:
            tok = wd["word"]
            tw = meas.textlength(tok, font=f_body)
            sw = meas.textlength(" ", font=f_body) if cur else 0
            if cur and (x + sw + tw - 40) > maxw:
                lines.append(cur)
                cur, x, sw = [], 40, 0
            x += sw
            wstarts.append((len(lines), x))
            cur.append(tok)
            x += tw
        if cur:
            lines.append(cur)
        lh, body_y = 38, 140
        wtimes = [ww["start"] - seg_start for ww in seg_words]

        def _glow_text(d, xy, s, font):
            x, y = xy
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                d.text((x + dx, y + dy), s, font=font, fill=GLOW)
            d.text((x, y), s, font=font, fill=GREEN)

        def frame_at(t):
            img = Image.new("RGB", (PW, PH), (0, 0, 0))
            d = ImageDraw.Draw(img)
            _glow_text(d, (40, 44), header, f_head)
            d.line([(40, 104), (PW - 40, 104)], fill=(0, 80, 6), width=2)
            last_vis = -1
            for wi, wt in enumerate(wtimes):
                if wt <= t:
                    last_vis = wi
                else:
                    break
            for wi in range(last_vis + 1):
                li, x = wstarts[wi]
                _glow_text(d, (x, body_y + li * lh),
                           seg_words[wi]["word"], f_body)
            if last_vis >= 0:
                li, x = wstarts[last_vis]
                tw = meas.textlength(seg_words[last_vis]["word"] + " ",
                                     font=f_body)
                cx, cy = x + tw, body_y + li * lh
                if t % 1.0 < 0.6:  # blinking block cursor
                    d.rectangle([cx, cy, cx + 15, cy + 30], fill=GREEN)
            # Right-edge separator: thin green rule between panel/visual.
            d.line([(PW - 2, 0), (PW - 2, PH)], fill=(0, 120, 8), width=3)
            return img

        n_frames = max(1, int(seg_dur * fps))
        frame_dur = seg_dur / n_frames
        fdir = seg_dir / f"panel_frames_{seg_idx:02d}"
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
             "-vf", "format=yuv420p",
             "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-preset", "veryfast", "-crf", "18", str(dest)])
        print(f"[render] terminal panel seg {seg_idx} "
              f"({dest.name}, {n_frames} frames, {len(seg_words)} words)")
        return str(dest)

    _script_mtime = (ROOT / "output" / "script.json").stat().st_mtime

    def _fresh(path):
        """True if a generated clip is newer than script.json — safe to
        reuse across re-runs (2026-10-13: the VM gets replaced mid-render,
        so re-runs must not redo the expensive PIL frame generation)."""
        p = Path(path)
        return p.exists() and p.stat().st_mtime > _script_mtime

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

    # Landscape: pre-render one terminal panel clip per segment (except
    # the intro, which is full-frame). Shots slice their time range out
    # of it, keeping typing in sync. (2026-10-13b: hooks use the split
    # too — the panel is their caption track.)
    panel_clips = {}
    if LANDSCAPE:
        for si, _seg in enumerate(script["segments"]):
            if si == 0:
                continue  # intro is full-frame terminal
            dest = seg_dir / f"panel_seg{si:02d}.mp4"
            if _fresh(dest):
                print(f"[render] terminal panel seg {si}: reusing "
                      f"{dest.name}")
            else:
                terminal_panel(si, dest)
            panel_clips[si] = str(dest)

    def render_landscape_shot(v, i, dur, seg, n, badge):
        """Landscape (16:9) shot builder (2026-10-13, rev 2026-10-13b).
        Layout:
        - cold-open intro (segment 0): full-frame wide terminal intro
          (intro_video adapts via the landscape constants).
        - EVERYTHING else (headline hooks, branding, story deep-dives):
          SPLIT — terminal panel (left third, sliced from the
          pre-rendered segment panel so typing stays in sync) + visual
          (right two-thirds). The panel is the caption track, so hooks
          show their narration (user 2026-10-13).
        Story shots carry the number badge top-right of the visual region;
        hooks carry the same number pill as stories (segment badge).
        Two-up: a shot with two_up/path2 renders both visuals side by
        side inside the visual region (data contract for the worker:
        mark the script shot "two_up": true with a "broll2" query;
        visuals.py resolves it to path2).
        """
        out = seg_dir / f"shot_{i:02d}.mp4"
        is_intro = (v.get("segment") == 0 and v.get("seg_kind") == "hook")
        is_branding = (v.get("seg_kind") == "hook"
                       and not seg.get("story_id")
                       and v.get("segment") != 0)
        # 2026-10-20.6: NO hardcoded analytics map. A per-day map lived
        # here and went stale every morning, overwriting the new script's
        # shots with the previous day's graphics (2026-10-20 evening run:
        # SpaceX giveaway math, hacker breach numbers, Nscale $90B bars and
        # AEGIS thresholds all fired on unrelated new stories). Analytics
        # now apply ONLY when the worker writes a per-run map for the
        # current script at pipeline/output/analytics_map.json
        # ({"<shot_index>": "<analytics_*.mp4>"}); no file = no override,
        # and the planned visuals render untouched.
        _analytics_map = {}
        _amap_path = ROOT / "output" / "analytics_map.json"
        if _amap_path.exists():
            try:
                import json as _json
                _analytics_map = {int(k): v for k, v in
                                  _json.loads(_amap_path.read_text()).items()}
                print(f"[render] analytics map from {_amap_path.name}: "
                      f"{_analytics_map}")
            except Exception as e:
                print(f"[render] WARNING: bad analytics_map.json: {e}")
        if i in _analytics_map:
            ap = ROOT / "cache" / "generated" / _analytics_map[i]
            if ap.exists():
                # 2026-10-13: mutate in place (not a copy) and stamp the
                # source, so visuals.json reflects what actually rendered.
                # QA's black-frame guard reads visuals.json — a stale
                # "duplicate-needs-review" there failed clean renders.
                v["kind"] = "clip"
                v["path"] = str(ap)
                v["source"] = "analytical-animation"
                print(f"[render] shot {i}: analytical animation "
                      f"({_analytics_map[i]})")
        if is_intro:
            anim = seg_dir / "intro_anim.mp4"
            if not _fresh(anim):
                seg0_end = timings[0]["start"] + timings[0]["duration"]
                iw = [ww for ww in words if ww["start"] < seg0_end]
                intro_video(script["segments"][0]["text"], iw, dur, anim,
                            load_story_people())
                print(f"[render] shot {i}: animated intro ({len(iw)} words)")
            else:
                print(f"[render] shot {i}: reusing intro_anim.mp4")
            v = dict(v, kind="clip", path=str(anim))
        if is_branding:
            # Self-plug (2026-10-10): Pixar character montage — NOT stock.
            # Fails LOUD if the clip is missing.
            clip = ROOT / "cache" / "generated" / "selfplug_pixar.mp4"
            if not clip.exists():
                raise FileNotFoundError(
                    f"[render] FATAL: self-plug clip missing: {clip}")
            v = dict(v, kind="clip", path=str(clip))
            print(f"[render] shot {i}: self-plug PIXAR clip ({clip.name})")

        def build_vis(path, is_clip, dest, vw, vh, max_w=None):
            """Encode one visual-region clip (vw x vh). Photos get the
            quick elastic zoom-out; clips play once and hold (no-loop).
            max_w caps the fitted image width (2026-10-13b: logo-only
            hook wordmarks would otherwise fill the region)."""
            if is_clip:
                vf = (f"format=rgb24,"
                      f"scale={vw}:{vh}:force_original_aspect_ratio=decrease,"
                      f"pad={vw}:{vh}:(ow-iw)/2:(oh-ih)/2:0x000000,"
                      f"fps={fps},setsar=1")
                _no_loop = ("analytics_" in path or "selfplug_" in path)
                if _no_loop:
                    try:
                        cp = subprocess.run(
                            ["ffprobe", "-v", "quiet", "-show_entries",
                             "format=duration", "-of", "csv=p=0", path],
                            capture_output=True, text=True, check=True)
                        c_dur = float(cp.stdout.strip())
                    except Exception:
                        c_dur = dur
                    if dur - c_dur > 0.02:
                        vf += (f",tpad=stop_mode=clone:"
                               f"stop_duration={dur - c_dur:.3f}")
                    base = ["-i", path]
                else:
                    base = ["-stream_loop", "-1", "-i", path]
                run(["ffmpeg", "-y"] + base + ["-t", f"{dur:.2f}", "-vf", vf, "-an",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-colorspace", "bt709", "-color_primaries",
                            "bt709", "-color_trc", "bt709",
                            "-color_range", "tv",
                            "-preset", preset, "-crf", "23", str(dest)])
            else:
                src = frame_layout(path, vw * 2, vh * 2,
                                   seg_dir / f"shot_{i:02d}_bg.jpg",
                                   landscape=True, max_w=max_w)
                frames = max(1, int(dur * fps))
                zmax = 1.05 if v.get("doc") else 1.12
                zf = min(frames, int(1.5 * fps))
                z = (f"if(lt(on,{zf}),"
                     f"1+{zmax - 1:.3f}*pow(1-on/{zf},2)"
                     f"*(1+0.45*sin(6.283*on/{zf})*(1-on/{zf}))"
                     f",1)")
                vf = (f"scale={vw*2}:{vh*2}:force_original_aspect_ratio=increase,"
                      f"crop={vw*2}:{vh*2},"
                      f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':"
                      f"y='ih/2-(ih/zoom/2)':d=1:s={vw}x{vh}:fps={fps},"
                      f"setsar=1")
                run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(fps),
                     "-i", src, "-t", f"{dur:.2f}", "-vf", vf, "-an",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-colorspace", "bt709", "-color_primaries", "bt709",
                     "-color_trc", "bt709", "-color_range", "tv",
                     "-preset", preset, "-crf", "23", str(dest)])
            return str(dest)

        # SPLIT (2026-10-13b): every non-intro shot — story deep-dives,
        # headline hooks, and branding — gets panel | visual. The panel is
        # the caption track, so hooks finally show their narration.
        if v.get("segment") in panel_clips:
            vis = seg_dir / f"shot_{i:02d}_vis.mp4"
            if v.get("two_up") and v.get("path2"):
                # Two visuals side by side inside the visual region.
                half = VIS_W // 2
                l = build_vis(v["path"], v["kind"] == "clip",
                              seg_dir / f"shot_{i:02d}_visL.mp4", half, h)
                r = build_vis(v["path2"], v["kind"] == "clip",
                              seg_dir / f"shot_{i:02d}_visR.mp4", half, h)
                run(["ffmpeg", "-y", "-i", l, "-i", r,
                     "-filter_complex", "[0:v][1:v]hstack=inputs=2",
                     "-t", f"{dur:.2f}", "-an", "-c:v", "libx264",
                     "-pix_fmt", "yuv420p", "-preset", preset, "-crf", "23",
                     str(vis)])
                print(f"[render] shot {i}: two-up visual")
            else:
                # Hooks (2026-10-13b): cap wordmark width so logo-only
                # pairs don't sprawl — 900px in the 1280px region.
                _mw = 1800 if v.get("seg_kind") == "hook" else None
                build_vis(v["path"], v["kind"] == "clip", vis, VIS_W, h,
                          max_w=_mw)
            tm = timings[v["segment"]]
            rel = max(0.0, v["start"] - tm["start"])
            fc = (f"[0:v]trim=start={rel:.3f}:end={rel + dur:.3f},"
                  f"setpts=PTS-STARTPTS[p];[p][1:v]hstack=inputs=2[stack]")
            inputs = ["-i", panel_clips[v["segment"]], "-i", str(vis)]
            _vmap = []
            if badge:
                # Badge top-right of the visual region (right edge at
                # frame right, clear of the end-screen zone). The overlay
                # is the unlabeled filtergraph output — ffmpeg auto-maps it.
                fc += f";[stack][2:v]overlay={w-291}:89"  # canvas centred on (w-198, 146)
                inputs += ["-loop", "1", "-i", badge]
            else:
                # No badge (hooks): map the labeled hstack output
                # explicitly — an unmapped labeled filtergraph output
                # is a fatal "unconnected" error.
                _vmap = ["-map", "[stack]"]
            run(["ffmpeg", "-y", *inputs,
                 "-filter_complex", fc,
                 "-t", f"{dur:.2f}", "-an", *_vmap,
                 "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-colorspace", "bt709", "-color_primaries", "bt709",
                 "-color_trc", "bt709", "-color_range", "tv",
                 "-preset", preset, "-crf", "23", str(out)])
            print(f"[render] shot {i}: split panel|visual "
                  f"(badge {n})" if badge else f"[render] shot {i}: split")
            return str(out)

        # Full-frame fallback: only the intro (segment 0) reaches here.
        if v["kind"] == "clip" and is_intro:
            vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},fps={fps},setsar=1")
            vf += ",fade=t=in:st=0:d=0.8"
            run(["ffmpeg", "-y", "-i", v["path"], "-t", f"{dur:.2f}",
                 "-vf", vf, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                 "-preset", preset, "-crf", "23", str(out)])
        else:
            # Shouldn't happen — every non-intro segment has a panel.
            # Render the visual full-frame rather than failing.
            print(f"[render] WARNING: shot {i} has no panel, full-frame "
                  f"fallback")
            build_vis(v["path"], v["kind"] == "clip", out, w, h)
        return str(out)

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
        seg = script["segments"][v["segment"]] \
            if v.get("segment", 0) < len(script["segments"]) else {}
        if LANDSCAPE:
            # Landscape path (2026-10-13): split terminal panel + visual.
            # The 9:16 code below is untouched.
            badge = None
            n = None
            if v.get("seg_kind") in ("story", "hook"):
                n = seg_number(v.get("segment"))
                if n:
                    badge = seg_dir / f"badge_{n}.png"
                    # Always regenerate (2026-10-23): a stale badge PNG
                    # from an older format would otherwise survive.
                    number_badge(n, badge)
                    badge = str(badge)
            render_landscape_shot(v, i, dur, seg, n, badge)
            _prev_badge_n = n if badge else None
            seg_files.append(out)
            continue
        # Intro (2026-10-09, CUT 2026-10-23): the video now starts with
        # the headline hooks — there is no cold-open segment any more.
        # A segment is only an intro if it is a story-less hook whose
        # text actually starts with "Breaking" (legacy scripts); the
        # first story hook (segment 0 after the cut, WITH a story_id)
        # must never be mistaken for it.
        # Branding hook ("link in bio"): the self-plug Pixar montage.
        is_intro = (v.get("seg_kind") == "hook"
                    and not seg.get("story_id")
                    and str(seg.get("text", "")).strip().lower()
                    .startswith("breaking"))
        is_branding = (v.get("seg_kind") == "hook"
                       and not seg.get("story_id")
                       and not is_intro)
        if is_intro:
            # Animated word-by-word intro (2026-10-09, legacy only) —
            # regenerated every run since the cold-open line is written
            # fresh daily.
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
        # 2026-10-20.6: NO hardcoded analytics map. A per-day map lived
        # here and went stale every morning, overwriting the new script's
        # shots with the previous day's graphics (2026-10-20 evening run:
        # SpaceX giveaway math, hacker breach numbers, Nscale $90B bars and
        # AEGIS thresholds all fired on unrelated new stories). Analytics
        # now apply ONLY when the worker writes a per-run map for the
        # current script at pipeline/output/analytics_map.json
        # ({"<shot_index>": "<analytics_*.mp4>"}); no file = no override,
        # and the planned visuals render untouched.
        _analytics_map = {}
        _amap_path = ROOT / "output" / "analytics_map.json"
        if _amap_path.exists():
            try:
                import json as _json
                _analytics_map = {int(k): v for k, v in
                                  _json.loads(_amap_path.read_text()).items()}
                print(f"[render] analytics map from {_amap_path.name}: "
                      f"{_analytics_map}")
            except Exception as e:
                print(f"[render] WARNING: bad analytics_map.json: {e}")
        if i in _analytics_map:
            ap = ROOT / "cache" / "generated" / _analytics_map[i]
            if ap.exists():
                # 2026-10-13: mutate in place (not a copy) and stamp the
                # source, so visuals.json reflects what actually rendered.
                # QA's black-frame guard reads visuals.json — a stale
                # "duplicate-needs-review" there failed clean renders.
                v["kind"] = "clip"
                v["path"] = str(ap)
                v["source"] = "analytical-animation"
                print(f"[render] shot {i}: analytical animation "
                      f"({_analytics_map[i]})")
        # Badge at middle-right of the top third (rule 12): every shot of
        # a story's deep-dive segment AND every headline hook carries the
        # same story-number pill there (2026-10-23: unified pill).
        # Badge PNGs are generated once and reused across the shots.
        # seg_number is None for story-less hooks (self-plug), so those
        # correctly get no pill.
        badge = None
        n = None
        if v.get("seg_kind") in ("story", "hook"):
            n = seg_number(v.get("segment"))
            if n:
                badge = seg_dir / f"badge_{n}.png"
                # Always regenerate (2026-10-23): see landscape branch.
                number_badge(n, badge)
                badge = str(badge)
                print(f"[render] shot {i}: story-number badge {n} "
                      f"middle-right of top third")

        # Number badge: story identifier at top-right, VERTICALLY CENTERED
        # on the watermark (watermark at y=190, 34pt -> center ~212).
        # 2026-10-23: the 138x66 pill is centred on the old pill centre
        # (W-198, 212), so the pill rect is W-267..W-129 x 179..245 and
        # its canvas (186x114, with the blur margin) overlays at
        # W-291:155. Right edge 951 sits clear of TikTok's 120px
        # right-rail zone, so the QA sidecar can now be honest.
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
                       f"scale=w='186*(0.92+0.08*{_be})'"
                       f":h='114*(0.92+0.08*{_be})':eval=frame,"
                       f"fade=t=in:st=0:d=0.4:alpha=1[bg];"
                       f"[base][bg]overlay=W-291:155")  # canvas centred on (W-198, 212)
            else:
                bvf = (f"{base_vf}[base];"
                       f"[1:v]format=rgba,scale=186:114[bg];"
                       f"[base][bg]overlay=W-291:155")  # canvas centred on (W-198, 212)
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
                # 2026-10-23 portrait-fill (user): clips that are close
                # to 9:16 cover-fill the frame; everything else gets a
                # blurred background from its own colours (same rule as
                # frame_layout for photos) with the sharp clip fit inside
                # the visual zone (y 0..1400). No black bars.
                # Analytical animations (2026-10-10): MUST sit below the
                # watermark/badge (badge bottom y=278) — pad y=290, no overlap
                # with badge, watermark, or captions; they keep the old path.
                _is_analytics = "analytics_" in v["path"]
                if _is_analytics:
                    vf = (f"format=rgb24,"
                          f"scale={w}:{REGION_H}:force_original_aspect_ratio=decrease,"
                          f"pad={w}:{h}:(ow-iw)/2:290:0x000000,"
                          f"fps={fps},setsar=1")
                else:
                    _cw, _ch = 0, 0
                    try:
                        _pr = subprocess.run(
                            ["ffprobe", "-v", "quiet", "-select_streams",
                             "v:0", "-show_entries", "stream=width,height",
                             "-of", "csv=p=0", v["path"]],
                            capture_output=True, text=True, check=True)
                        _cw, _ch = [int(x) for x in
                                    _pr.stdout.strip().split(",")[:2]]
                    except Exception:
                        pass
                    _ta = w / h
                    _sa = (_cw / _ch) if _cw and _ch else 0
                    _loss = (1.0 - _ta / _sa) if _sa >= _ta else \
                        (1.0 - _sa / _ta) if _sa else 1.0
                    # 2026-10-23 (frame-review fix): the self-plug clip
                    # must NEVER cover-fill. Its 1080x1400 canvas is
                    # designed to sit in the visual zone above the
                    # captions; cover-filling it to 1080x1920 stretches
                    # it to full height and pushes its bottom row
                    # under the caption black area. Force the blur-pad
                    # path for selfplug clips, so the group stays in
                    # y 0..1400 and fully visible above the captions.
                    if _sa and _loss <= 0.30 and "selfplug_" not in v["path"]:
                        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                              f"crop={w}:{h},fps={fps},setsar=1")
                    else:
                        # Blur-pad: background is the clip itself, scaled
                        # down, blurred, scaled back up (cheaper than a
                        # full-res blur per frame) and darkened; the sharp
                        # clip sits centred in the visual zone on top.
                        vf = (f"split[bs][fs];"
                              f"[bs]scale=540:960:force_original_aspect_ratio=increase,"
                              f"crop=540:960,gblur=sigma=20,scale={w}:{h},"
                              f"eq=brightness=-0.18[bg0];"
                              f"[fs]scale={w}:1400:force_original_aspect_ratio=decrease"
                              f"[fg0];[bg0][fg0]overlay=(W-w)/2:(1400-h)/2,"
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
                               seg_dir / f"shot_{i:02d}_bg.jpg",
                               doc=bool(v.get("doc")),
                               person=bool(v.get("person")))
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

    # 2026-10-13: persist render-time visual overrides (analytics map,
    # hook pairs) so visuals.json describes what actually shipped.
    # QA reads this file; stale "black-frame"/"duplicate-needs-review"
    # sources here failed renders that were visually clean.
    (ROOT / "output" / "visuals.json").write_text(
        json.dumps(visuals, indent=2))
    print("[render] visuals.json updated with render-time overrides")

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

    # 2026-10-23 caption background (user): terminal captions stay, but
    # their area gets a PURE BLACK background whose top edge fades
    # (soft gradient, no solid line) instead of the old floating text
    # over whatever the shot happened to show. This matters now that
    # shots fill the frame (item 2) — without it, a full-bleed shot
    # would bleed under the captions. The gradient is composited in
    # Pass 2 itself (overlay first, then ASS captions on top) — NOT as
    # a separate pre-pass encode: a pre-pass double-encodes the whole
    # video (2026-10-23: the pre-pass was still running at 30+ min when
    # a service restart killed it, with the final encode still to come).
    # Landscape keeps its terminal panel (no gradient).
    grad_path = None
    if not LANDSCAPE:
        try:
            grad_path = caption_gradient_png(
                ROOT / "output" / "caption_gradient.png")
        except Exception as e:
            print(f"[render] WARNING: caption gradient failed ({e}) — "
                  f"continuing without it")

    # MUSIC OFF (2026-10-23, user, temporary): the bed track is
    # preserved as assets/music/ai_digest_bed.mp3.disabled, so no
    # *.mp3 track exists and no bed is mixed until the user asks again.
    # 2026-10-23 beat-synced music bed (user, via beats.py): when a music
    # track exists, align its loop to whole beats (first beat at the
    # bed start, loop length = a whole number of beats) instead of
    # looping a raw mp3 that can cut mid-beat. Falls back silently to
    # the old raw loop if beat detection fails; no music = no bed.
    if music:
        try:
            from beats import beat_aligned_bed
            _ndur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "csv=p=0", str(narration)],
                capture_output=True, text=True).stdout.strip() or 60)
            _bed = beat_aligned_bed(str(music), _ndur,
                                    ROOT / "output" / "music_bed.wav")
            if _bed:
                music = Path(_bed)
                print(f"[render] music bed beat-aligned -> {music.name}")
        except Exception as e:
            print(f"[render] WARNING: beat alignment failed ({e}) — "
                  f"using raw music loop")

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
    # Landscape (2026-10-13): the terminal panel IS the caption track —
    # no ASS captions are burned. (2026-10-13b: hooks use the split
    # layout too, so the panel covers them — only the intro is full-frame,
    # and it types its own text.)
    if not LANDSCAPE:
        vf_parts.append(f"ass={captions}")
    # Watermark (2026-10-10): "@leos.logos" at 50%. Landscape: top-left
    # of the visual region, aligned with the badge top (y=80).
    if LANDSCAPE:
        vf_parts.append(
            "drawtext=text='@leos.logos':fontfile=/usr/share/fonts/truetype/"
            f"dejavu/DejaVuSans-Bold.ttf:x={VIS_X + 40}:y=80:fontsize=34:"
            "fontcolor=white@0.5")
    else:
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

    emph_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {1920 if LANDSCAPE else 1080}
PlayResY: {1080 if LANDSCAPE else 1920}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Emphasis,Arial,76,&H00FFFFFF,&H00000000,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,8,0,5,60,60,60,1
# (HookNum style retired 2026-10-23: hooks now carry the same PNG pill
# as stories, composited in the segment stage — no ASS number pill.)

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    emph_events = []
    # Overlay geometry sidecar for QA safe-area checks (2026-10-11,
    # motion-skills audit): every burned-in overlay's rect/anchor, so qa.py
    # can verify nothing sits under platform UI zones. Single source of
    # truth — these are the same constants used to place the overlays.
    if LANDSCAPE:
        # Landscape (2026-10-13): badge top-right of the visual region,
        # watermark top-left of the visual region, hook pill centered on
        # the badge. No captions/emphasis anchors — the terminal panel is
        # layout, not an overlay.
        overlay_geoms = [
            {"name": "story_badge",
             "rect": [w - 267, 113, w - 129, 179]},
            {"name": "watermark", "rect": [VIS_X + 40, 80, VIS_X + 280, 118]},
            {"name": "hook_num_pill",
             "rect": [w - 267, 113, w - 129, 179]},
        ]
    else:
        overlay_geoms = [
            {"name": "story_badge",
             "rect": [w - 267, 179, w - 129, 245]},
            {"name": "watermark", "rect": [60, 190, 300, 228]},
            {"name": "hook_num_pill",
             # Unified pill (2026-10-23): same rect as the story badge.
             "rect": [w - 267, 179, w - 129, 245]},
            {"name": "captions", "anchor": [60, 1450]},
        ]
    story_ids = {str(sid).lower().replace("-", " ").replace("_", " ")
                 for sid in script.get("story_ids", [])}
    for si, seg in enumerate(script["segments"]):
        # Rule 12 (unified 2026-10-23): story hooks carry the same PNG
        # number pill as their deep-dive, composited in the segment
        # stage -- NOT an ASS event here, which used to look different
        # (#n, tight black box) and would double up with the badge.
        # Hooks get no emphasis pill.
        if seg.get("kind") == "hook":
            continue
        if LANDSCAPE:
            # Landscape (2026-10-13): story emphasis pills are skipped —
            # the terminal panel already shows the narration as it's
            # spoken. Hook number pills are the segment badge now.
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
        # 2026-10-17: the emphasis pill is redundant on analytical-
        # animation shots — the graphic IS the punch (a pill reading
        # "24 YEARS OF HOSPITAL DATA" lands on top of a graphic reading
        # "24 / YEARS OF HOSPITAL BED DATA"). Skip the pill when its
        # window overlaps an analytical shot.
        if any(v.get("source") == "analytical-animation"
               and v.get("start", 0) < eend
               and v.get("start", 0) + v.get("duration", 0) > estart
               for v in visuals):
            print(f"[render] emphasis seg{si}: skipped — analytical shot "
                  f"owns the punch")
            continue
        # Face-aware placement (2026-10-13, user: "emphasis should show
        # up above or below any faces"). ROOT CAUSE of covers: the old
        # code stored only the face CENTER and snapped to 960 vs 320 on
        # a 0.5 threshold — a large face, a face near the boundary, or a
        # missed detection still got covered. Now: the full face box is
        # stored (detect_face returns [cx,cy,w,h]); the pill goes to the
        # third-center (320/960/1600) whose band doesn't touch the face
        # box (120px margin). Person shot with no detected face -> top
        # (faces usually sit center/middle, so top is the safe default).
        # Non-person shot -> middle.
        face_box = None  # (top_y, bottom_y) in frame px
        is_person_shot = False
        for v in visuals:
            if (v.get("segment") == si
                    and not (v["start"] + v["duration"] <= estart
                             or v["start"] >= eend)):
                if v.get("person"):
                    is_person_shot = True
                fx = v.get("face_xy")
                if fx and len(fx) >= 4:
                    cx, cy, fw, fh = fx[0], fx[1], fx[2], fx[3]
                    top = (cy - fh / 2) * h
                    bot = (cy + fh / 2) * h
                    if face_box is None or (bot - top) > (face_box[1] - face_box[0]):
                        face_box = (top, bot)
                if face_box:
                    break
        thirds = [h // 6, h // 2, 1400]  # 1400: above captions (1450)
        # and clear of the bottom-20% UI zone (1536+). Never use 1600.
        if face_box:
            ftop, fbot = face_box[0] - 120, face_box[1] + 120
            # Pill half-height ~70px; a third is safe if the pill band
            # [y-70, y+70] doesn't intersect the expanded face box.
            safe = [y for y in thirds
                    if y + 70 < ftop or y - 70 > fbot]
            if safe:
                # Farthest safe third from the face center wins.
                fcenter = (face_box[0] + face_box[1]) / 2
                y = max(safe, key=lambda yy: abs(yy - fcenter))
            else:
                y = thirds[0]  # face fills frame; top is least bad
            print(f"[render] emphasis seg{si}: face box "
                  f"{int(face_box[0])}-{int(face_box[1])} -> pill y={y}")
        elif is_person_shot:
            y = thirds[0]
        else:
            y = thirds[1]
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
    if grad_path and not LANDSCAPE:
        # Gradient in the SAME encode as captions: video chain is
        # overlay (black fade at y=1380) -> tpad -> ASS captions ->
        # watermark -> emphasis ASS, all in one filter_complex with the
        # audio filter. Gradient input index = 2 without music, 3 with.
        gidx = 3 if music else 2
        vchain = (f"[0:v][{gidx}:v]overlay=0:1380:format=yuv420,"
                  f"format=yuv420p")
        if vf_parts:
            vchain += "," + ",".join(vf_parts)
        vchain += "[vout]"
        run(["ffmpeg", "-y", *inputs, "-loop", "1", "-i", str(grad_path),
             "-filter_complex", f"{vchain};{afilter}",
             "-map", "[vout]", "-map", amap,
             "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-profile:v", "high", "-level", "4.0",
             "-preset", preset, "-crf", str(crf),
             "-r", str(fps), "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
             "-shortest", "-movflags", "+faststart", str(final)])
    else:
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
    if LANDSCAPE:
        # YouTube chapters for the video description (2026-10-13):
        # story start times + titles, in story order.
        def _mmss(sec):
            m, s = divmod(int(sec), 60)
            return f"{m:02d}:{s:02d}"
        titles = {}
        for src_i, sid in enumerate(script.get("story_ids", [])):
            srcs = script.get("sources", [])
            titles[str(sid)] = (srcs[src_i]["title"]
                                if src_i < len(srcs) else str(sid))
        lines = ["00:00 Intro"]
        for si, seg in enumerate(script["segments"]):
            sid = str(seg.get("story_id") or "")
            if seg.get("kind") == "story" and sid and si < len(timings):
                n = story_num.get(sid, 0)
                lines.append(f"{_mmss(timings[si]['start'])} "
                             f"#{n} {titles.get(sid, sid)}")
        (ROOT / "output" / "chapters_landscape.txt").write_text(
            "\n".join(lines) + "\n")
        print(f"[render] chapters_landscape.txt ({len(lines)} chapters)")


if __name__ == "__main__":
    main()
