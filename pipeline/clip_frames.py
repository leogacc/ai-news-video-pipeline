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
import os
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageFont

TITLE_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TERMINAL_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
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


def draw_overlay_box(canvas, y0, y1, lines, size, fonts=None):
    """Draw a feathered semi-transparent text block directly onto an RGBA overlay."""
    box_w = BOX_W
    box_h = y1 - y0
    box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    mask = Image.new("L", (box_w, box_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=18, fill=230)
    mask = mask.filter(ImageFilter.GaussianBlur(12))

    fill_layer = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 190))
    box_img.paste(fill_layer, (0, 0), mask)
    canvas.alpha_composite(box_img, (BOX_X, y0))

    draw = ImageDraw.Draw(canvas)
    lh = size + 14
    total_h = lh * len(lines)
    ty = y0 + (y1 - y0 - total_h) // 2
    for i, ln in enumerate(lines):
        f = ImageFont.truetype(fonts[i] if fonts else TITLE_FONT, size)
        w = draw.textlength(ln, font=f)
        draw.text(((1080 - w) // 2, ty), ln, font=f, fill=(255, 255, 255, 255))
        ty += lh


def build_video_overlay(title_lines, bio_lines, video_w, video_h, max_w=960):
    """Generate a transparent 1080x1920 RGBA overlay for a moving video shot.

    Returns:
        (overlay_image, layout_dict)
        where layout_dict has: nw, nh, content_top, content_bottom, title, bio
    """
    nw, nh, content_top, t0, t1, b0, b1 = hug_layout(
        len(title_lines), len(bio_lines), video_w, video_h, max_w=max_w
    )
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw_overlay_box(overlay, t0, t1, title_lines, 46)

    bio_fonts = [BIO_FONT if ln.startswith("Source:") else TITLE_FONT for ln in bio_lines]
    draw_overlay_box(overlay, b0, b1, bio_lines, 34, fonts=bio_fonts)

    # Watermark beneath bio (user, 2026-11-05): x=60, bio bottom + 20px, alpha 51
    wmf = ImageFont.truetype(TITLE_FONT, 34)
    _wmd = ImageDraw.Draw(overlay)
    _bb = _wmd.textbbox((0, 0), "@leos.logos", font=wmf)
    _wm_h = _bb[3] - _bb[1]
    _wm_y = min(b1 + 20, 1495 - _wm_h) - _bb[1]
    _wmd.text((60, _wm_y), "@leos.logos", font=wmf, fill=(255, 255, 255, 51))

    layout = {
        "nw": nw,
        "nh": nh,
        "content_top": content_top,
        "content_bottom": content_top + nh,
        "title": (t0, t1),
        "bio": (b0, b1),
    }
    return overlay, layout


def build_terminal_window_overlay(
    box_top: int = 1150,
    box_height: int = 275,
    width: int = 960,
) -> Image.Image:
    """Generate a transparent 1080x1920 RGBA overlay featuring a frosted dark terminal console window.

    - Centered horizontally: x0 = (1080 - width) // 2 (= 60 for width=960), x1 = x0 + width (= 1020)
    - Vertical span: y0 = box_top (= 1150), y1 = box_top + box_height (= 1425)
    - Frosted dark console background: rgba(11, 15, 25, 0.92) -> (11, 15, 25, 235)
    - Border: 1px solid rgba(0, 242, 254, 0.28) with rounded corners (radius 18)
    - Title bar / window controls: Red dot (#FF5F56), Yellow dot (#FFBD2E), Green dot (#27C93F)
      with 12px diameter located at y ≈ y0 + 19 (centers x0 + 24, x0 + 44, x0 + 64)
    - Monospace title: 'bash — ai-news@terminal' centered horizontally in title bar (y ≈ y0 + 10)
    """
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    x0 = (1080 - width) // 2
    x1 = x0 + width
    y0 = box_top
    y1 = box_top + box_height

    # Draw rounded dark console window
    draw.rounded_rectangle(
        [x0, y0, x1 - 1, y1 - 1],
        radius=18,
        fill=(11, 15, 25, 235),
        outline=(0, 242, 254, 70),
        width=1,
    )

    # Title bar divider line at y0 + 38
    draw.line(
        [(x0 + 1, y0 + 38), (x1 - 2, y0 + 38)],
        fill=(0, 242, 254, 40),
        width=1,
    )

    # Traffic light control dots: 12px diameter (r = 6)
    cy = y0 + 19
    r = 6
    controls = [
        (x0 + 24, (255, 95, 86, 255)),   # Red #FF5F56
        (x0 + 44, (255, 189, 46, 255)),  # Yellow #FFBD2E
        (x0 + 64, (39, 201, 63, 255)),   # Green #27C93F
    ]
    for cx, color in controls:
        draw.ellipse([cx - r, cy - r, cx + r - 1, cy + r - 1], fill=color)

    # Monospace title centered horizontally in title bar
    title_text = "bash — ai-news@terminal"
    font_path = TERMINAL_FONT
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    try:
        font = ImageFont.truetype(font_path, 15)
    except Exception:
        font = ImageFont.load_default()

    tw = draw.textlength(title_text, font=font)
    tx = x0 + (width - tw) // 2
    ty = y0 + 10
    draw.text((tx, ty), title_text, font=font, fill=(180, 195, 215, 210))

    return overlay


def build_persistent_hook_banner(
    text: str,
    badge: str = "",
    width: int = 960,
    height: int = 110,
    y_top: int = 240,
) -> Image.Image:
    """Generate a transparent 1080x1920 RGBA overlay featuring a high-contrast persistent hook banner.

    Visual characteristics:
    - High-contrast brilliant white rounded pill (#FFFFFF) with 24px corner radius.
    - Subtle drop shadow (rgba(0, 0, 0, 0.38)) for sharp separation against any background footage.
    - Bold uppercase black typography (#0A0E16) dynamically auto-fitted (28-36pt).
    - Top safe-zone positioning (y: 240..350) safely below TikTok navigation header (y <= 220).
    - Designed to persist across Shot 0 and Shot 1 to hook users scrolling on mute.
    """
    overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    x0 = (1080 - width) // 2
    x1 = x0 + width
    y0 = y_top
    y1 = y0 + height

    # Soft drop shadow
    draw.rounded_rectangle([x0, y0 + 6, x1 - 1, y1 + 5], radius=24, fill=(0, 0, 0, 95))

    # Brilliant white rounded pill
    draw.rounded_rectangle(
        [x0, y0, x1 - 1, y1 - 1],
        radius=24,
        fill=(255, 255, 255, 252),
        outline=(225, 230, 240, 255),
        width=2,
    )

    font_path = TITLE_FONT if os.path.exists(TITLE_FONT) else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    clean_text = text.strip()
    if badge and not clean_text.startswith(badge):
        clean_text = f"{badge} {clean_text}"

    max_text_w = width - 60
    font_size = 36
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    tw = draw.textlength(clean_text, font=font)
    while tw > max_text_w and font_size > 28:
        font_size -= 2
        try:
            font = ImageFont.truetype(font_path, font_size)
            tw = draw.textlength(clean_text, font=font)
        except Exception:
            break

    if tw <= max_text_w:
        tx = x0 + (width - tw) // 2
        bbox = draw.textbbox((0, 0), clean_text, font=font)
        th = bbox[3] - bbox[1]
        ty = y0 + (height - th) // 2 - bbox[1]
        draw.text((tx, ty), clean_text, font=font, fill=(10, 14, 22, 255))
    else:
        # Wrap into 2 balanced lines
        words = clean_text.split()
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
        try:
            f2 = ImageFont.truetype(font_path, 26)
        except Exception:
            f2 = font
        lh = 32
        total_th = lh * 2
        ty = y0 + (height - total_th) // 2
        for ln in (line1, line2):
            w = draw.textlength(ln, font=f2)
            tx = x0 + (width - w) // 2
    return overlay


def build_terminal_evidence_card(
    out_path: str | Path,
    title: str = "evals_verifier.py",
    author: str = "AI Lab",
    metrics: list[str] | None = None,
) -> Path:
    """Generate a crisp, dark-mode terminal code execution card (960x600) for concrete evidence shots."""
    out_path = Path(out_path)
    img = Image.new("RGB", (960, 600), color=(11, 15, 25))
    draw = ImageDraw.Draw(img)

    # Window border & controls
    draw.rounded_rectangle([(10, 10), (950, 590)], radius=16, outline=(0, 242, 254), width=2)
    draw.line([(10, 55), (950, 55)], fill=(0, 242, 254, 100), width=1)
    for cx, c in [(35, (255, 95, 86)), (55, (255, 189, 46)), (75, (39, 201, 63))]:
        draw.ellipse([cx - 5, 30 - 5, cx + 5, 30 + 5], fill=c)

    font_path = TERMINAL_FONT if os.path.exists(TERMINAL_FONT) else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
    try:
        title_font = ImageFont.truetype(font_path, 16)
        code_font = ImageFont.truetype(font_path, 20)
    except Exception:
        title_font = ImageFont.load_default()
        code_font = ImageFont.load_default()

    draw.text((105, 20), f"{title} — bash", font=title_font, fill=(160, 180, 205))

    lines = metrics or [
        f"$ ./verify_system.sh --target {author.lower().replace(' ', '_')}",
        "[INIT] Loading open weights checkpoint into VRAM...",
        "[EVAL] Reasoning trace verified against ground truth",
        "[PASS] Capability benchmark verified: 93.2%",
        "+ Status: 100% reproducible on local hardware",
    ]

    y = 85
    for ln in lines:
        if ln.startswith("+") or "PASS" in ln or "verified" in ln:
            color = (57, 255, 20)
        elif ln.startswith("$"):
            color = (0, 242, 254)
        elif "INIT" in ln or "EVAL" in ln:
            color = (255, 189, 46)
        else:
            color = (220, 225, 235)
        draw.text((40, y), ln, font=code_font, fill=color)
        y += 42

    img.save(str(out_path))
    return out_path


def build_pattern_interrupt_card(
    out_path: str | Path,
    headline: str = "WAIT FOR IT...",
    subline: str = "PATTERN INTERRUPT",
    theme: str = "glitch",
) -> Path:
    """Generate a high-contrast chromatic aberration glitch card (960x600) for pattern interrupt cuts.

    Resets viewer cognitive fatigue at the 75% video mark before the climactic benchmark and CTA.
    """
    out_path = Path(out_path)
    img = Image.new("RGB", (960, 600), color=(8, 10, 18))
    draw = ImageDraw.Draw(img)

    # Chromatic aberration glitch border
    draw.rounded_rectangle([(14, 14), (954, 594)], radius=20, outline=(255, 0, 85), width=2)
    draw.rounded_rectangle([(8, 8), (948, 588)], radius=20, outline=(0, 242, 254), width=2)
    draw.rounded_rectangle([(10, 10), (950, 590)], radius=20, outline=(255, 255, 255), width=1)

    font_path = TITLE_FONT if os.path.exists(TITLE_FONT) else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        f_badge = ImageFont.truetype(font_path, 18)
        f_head = ImageFont.truetype(font_path, 44)
        f_sub = ImageFont.truetype(font_path, 20)
    except Exception:
        f_badge = ImageFont.load_default()
        f_head = ImageFont.load_default()
        f_sub = ImageFont.load_default()

    # Badge pill
    draw.rounded_rectangle([(360, 75), (600, 120)], radius=12, fill=(255, 0, 85))
    draw.text((480, 97), subline, font=f_badge, fill=(255, 255, 255), anchor="mm")

    # Headline with glitch shadow
    draw.text((482, 282), headline, font=f_head, fill=(255, 0, 85), anchor="mm")
    draw.text((478, 278), headline, font=f_head, fill=(0, 242, 254), anchor="mm")
    draw.text((480, 280), headline, font=f_head, fill=(255, 255, 255), anchor="mm")

    # Subtext
    draw.text((480, 420), "RESETTING COGNITIVE ATTENTION", font=f_sub, fill=(160, 180, 205), anchor="mm")
    img.save(str(out_path))
    return out_path




