#!/usr/bin/env python3
"""Shared narrated-clip frame builder (pipeline level, v2026.11.01.1).

DYNAMIC HUG RULE (user, 2026-11-01, on the HackerTube clip):
the title (top) and bio (bottom) text blocks must DYNAMICALLY HUG the
mid content on every shot — no dead space between text and content.
The old fixed zones (title y135..345, content y375..1325, bio
y1370..1500) left 170-280px black gaps around short content; the
hug kills them.

Layout, per shot (1080x1920):
- Content stays centred in the middle zone y375..1325 (950 tall),
  scaled to max 960 wide, on clean black (no-blur rule 2026-10-30).
- Title box sits directly above the content: box bottom =
  content_top - GAP. Bio box sits directly below: box top =
  content_bottom + GAP. GAP = 20px box-to-content.
- Boxes are sized to their text, not fixed height: title line
  height 60 (46px font + 14) + 20px padding top/bottom; bio line
  height 48 (34px font + 14) + 16px padding top/bottom. Resulting
  WHITE-TEXT-to-content gaps are 40px (title side) and 36px (bio
  side) — the same 36-40px standard the no-face layout already uses.
- Hard limits, always enforced: title top never above y130 (layout
  margin; the watermark now sits beneath the bio and no longer
  constrains the title); bio bottom never
  below y1500 (keeps the ~30px gap to the top-anchored captions at
  glyph row ~1530). The content max height is capped so the bio
  can never overflow: max_h = min(950, 2 * (630 - bio_h)).
  With a 2-line bio (128px) the cap is 950 (unchanged); a 3-line
  bio (176px) caps content at 908px.
- This supersedes the fixed narrated zones and the y1400
  stack-bottom check for narrated clips: with hugging, short
  content yields balanced margins, not a top-heavy frame, and the
  gap that matters is text-to-content (36-40px), not bio-to-frame.

Watermark: @leos.logos, DejaVuSans-Bold 34pt, white 20% opaque
(80% transparent, alpha 51), x=60, directly beneath the bio
block (bio bottom + 20px; clamped so its bottom never passes
y1495, keeping the gap to the top-anchored captions), on every
frame. It may overlap the mid content (user, 2026-11-05 — supersedes
the middle-left placement from earlier the same day and the old
top-left (60,80) 50% placement).
"""
from PIL import Image, ImageFilter, ImageDraw, ImageFont

TITLE_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
# 2026-11-04 SOURCE-REGULAR RULE (user: "Have the Find source text not
# be bold"): the bio block's Source line renders in REGULAR weight.
# 2026-11-05 the bio is a single Source line (the finding line was
# dropped, see bio_source_only_2026_11_05) — so every bio line goes
# regular. Title lines stay bold. Applies to narrated clips here and to
# source-video clip builds (same rule, their own overlay code).
BIO_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOX_X, BOX_W = 60, 960
GAP = 20
TITLE_LH, TITLE_PAD = 60, 20   # 46px font + 14; padding top/bottom
BIO_LH, BIO_PAD = 48, 16       # 34px font + 14; padding top/bottom
ZONE_TOP, ZONE_H = 375, 950    # content zone y375..1325
REGION_TOP = 130               # title top floor (layout margin)
CAPTION_FLOOR = 1500           # bio bottom ceiling (captions at ~1530)


def _box_h(n_lines, lh, pad):
    return lh * n_lines + 2 * pad


def hug_layout(n_title_lines, n_bio_lines, img_w, img_h, max_w=960):
    """Return (nw, nh, content_top, title_y0, title_y1, bio_y0, bio_y1).

    Guarantees: title_y0 >= 130, bio_y1 <= 1500, boxes never overlap
    the content, box-to-content gaps exactly GAP.
    """
    title_h = _box_h(n_title_lines, TITLE_LH, TITLE_PAD)
    bio_h = _box_h(n_bio_lines, BIO_LH, BIO_PAD)
    # Bio bottom = content_bottom + GAP + bio_h, with content_bottom
    # at most ZONE_TOP + ZONE_H (centred content). Cap content height
    # so the bio can never pass the caption floor.
    max_h = min(ZONE_H, 2 * (CAPTION_FLOOR - GAP - bio_h - ZONE_TOP - ZONE_H // 2))
    # NOTE: centred content bottom = ZONE_TOP + ZONE_H/2 + nh/2, so the
    # cap above simplifies to nh <= 2*(CAPTION_FLOOR - GAP - bio_h
    # - ZONE_TOP - ZONE_H/2). For a 2-line bio: 2*(1500-20-128-375-475)
    # = 1004 -> capped by ZONE_H 950. For a 3-line bio: 908.
    scale = min(max_w / img_w, max_h / img_h)
    nw, nh = int(img_w * scale), int(img_h * scale)
    content_top = ZONE_TOP + (ZONE_H - nh) // 2
    content_bottom = content_top + nh
    title_y1 = content_top - GAP
    title_y0 = title_y1 - title_h
    bio_y0 = content_bottom + GAP
    bio_y1 = bio_y0 + bio_h
    assert title_y0 >= REGION_TOP, f"title top {title_y0} < {REGION_TOP}"
    assert bio_y1 <= CAPTION_FLOOR, f"bio bottom {bio_y1} > {CAPTION_FLOOR}"
    assert title_y1 + GAP == content_top and bio_y0 == content_bottom + GAP
    return nw, nh, content_top, title_y0, title_y1, bio_y0, bio_y1


def draw_box(canvas, y0, y1, lines, size, fonts=None):
    """Draw a feathered text block. fonts, when given, is a font path per
    line (default: all TITLE_FONT bold)."""
    region = canvas.crop((BOX_X, y0, BOX_X + BOX_W, y1))
    blurred = region.filter(ImageFilter.GaussianBlur(12))
    darkened = Image.blend(blurred, Image.new("RGB", (BOX_W, y1 - y0), (0, 0, 0)), 0.5)
    mask = Image.new("L", (BOX_W, y1 - y0), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, BOX_W - 1, y1 - y0 - 1], radius=18, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(18))
    canvas.paste(darkened, (BOX_X, y0), mask)
    draw = ImageDraw.Draw(canvas)
    lh = size + 14
    total_h = lh * len(lines)
    ty = y0 + (y1 - y0 - total_h) // 2
    for i, ln in enumerate(lines):
        f = ImageFont.truetype(fonts[i] if fonts else TITLE_FONT, size)
        w = draw.textlength(ln, font=f)
        draw.text(((1080 - w) // 2, ty), ln, font=f, fill=(255, 255, 255))
        ty += lh


def build_frame(src, title_lines, bio_lines):
    """Render one 1080x1920 narrated-clip frame with the hug layout."""
    im = Image.open(src).convert("RGB")
    canvas = Image.new("RGB", (1080, 1920), (0, 0, 0))
    nw, nh, content_top, t0, t1, b0, b1 = hug_layout(
        len(title_lines), len(bio_lines), im.size[0], im.size[1])
    sharp = im.resize((nw, nh), Image.LANCZOS)
    canvas.paste(sharp, ((1080 - nw) // 2, content_top))
    draw_box(canvas, t0, t1, title_lines, 46)
    # SOURCE-REGULAR RULE (2026-11-04): the bio's Source line goes
    # regular. (2026-11-05: the bio is a single Source line — the
    # finding line was dropped — so every bio line gets BIO_FONT.)
    bio_fonts = [BIO_FONT if ln.startswith("Source:") else TITLE_FONT
                 for ln in bio_lines]
    draw_box(canvas, b0, b1, bio_lines, 34, fonts=bio_fonts)
    wmf = ImageFont.truetype(TITLE_FONT, 34)
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    # WATERMARK BENEATH THE BIO (user, 2026-11-05): x=60, directly
    # below the bio block (bio bottom + 20px); 80% transparent =
    # 20% opaque (alpha 51). It may overlap the mid content.
    # Clamped so its bottom never passes y1495 (keeps the ~35px gap
    # to the top-anchored captions at glyph row ~1530); on a shot
    # whose bio bottoms at the 1500 cap it rides the bio's lower
    # edge instead.
    _wmd = ImageDraw.Draw(overlay)
    _bb = _wmd.textbbox((0, 0), "@leos.logos", font=wmf)
    _wm_h = _bb[3] - _bb[1]
    _wm_y = min(b1 + 20, 1495 - _wm_h) - _bb[1]
    _wmd.text((60, _wm_y), "@leos.logos", font=wmf, fill=(255, 255, 255, 51))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    return canvas, {"nw": nw, "nh": nh, "content_top": content_top,
                    "content_bottom": content_top + nh,
                    "title": (t0, t1), "bio": (b0, b1)}
