#!/usr/bin/env python3
"""Self-plug emotion montage (canonical generator, 2026-10-10; face-driven
rewrite 2026-10-11): animates the CURRENT intro_people.png with a close-up
of EACH detected person (face-driven, never hardcoded), then a group settle.
No text, no terminal symbols — just the characters. 5.69s to match the
branding shot duration. render.py unconditionally substitutes the output
at cache/generated/selfplug_pixar.mp4 for the branding segment and fails
loudly if missing. Regenerate daily after intro_people.png changes.

ROOT CAUSE FIX (2026-10-11): the old code hardcoded 3 character boxes
tuned for one specific 3-person portrait (Elon/Middle/Son fractions).
With 4 people the boxes landed BETWEEN faces and cut them off, and the
4th person never got a close-up. Now YuNet detects every face, sorts
left-to-right, and each close-up is centered on its face — the person
count and positions always match the actual image.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
# 2026-10-23 (user review fix): the self-plug clip is now the full
# visual zone, 1080x1400, not 1080x1220 — the old canvas left the group
# as a landscape strip inside the portrait frame.
W, H, FPS = 1080, 1400, 30
DUR = 5.69
GROUP_DUR = 1.5  # group settle at the end; the rest splits per person
FACE_MODEL = ROOT / "cache" / "models" / "face_yunet.onnx"


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def detect_faces(path):
    """All faces in the image as [(cx, cy, w, h)] in pixels, sorted
    left-to-right. Empty list when none found / model missing."""
    try:
        import cv2
        img = cv2.imread(str(path))
        if img is None or not FACE_MODEL.exists():
            return []
        ih, iw = img.shape[:2]
        det = cv2.FaceDetectorYN_create(str(FACE_MODEL), "", (iw, ih),
                                        0.5, 0.3, 5000)
        _, faces = det.detect(img)
        if faces is None or len(faces) == 0:
            return []
        boxes = [(f[0] + f[2] / 2, f[1] + f[3] / 2, f[2], f[3]) for f in faces]
        # 2026-10-12: dedupe overlapping detections (YuNet can fire twice
        # on the same face — e.g. two boxes on one portrait). Merge boxes
        # with IoU > 0.15 or one box's center inside the other, keeping
        # the larger one.
        def _iou(a, b):
            ax0, ay0, ax1, ay1 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
            bx0, by0, bx1, by1 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
            ix, iy = max(0, min(ax1, bx1) - max(ax0, bx0)), max(0, min(ay1, by1) - max(ay0, by0))
            ia = ix * iy
            if ia == 0:
                return 0.0
            return ia / (a[2] * a[3] + b[2] * b[3] - ia)

        def _inside(a, b):
            # is box a's center inside box b?
            bx0, by0 = b[0] - b[2] / 2, b[1] - b[3] / 2
            bx1, by1 = b[0] + b[2] / 2, b[1] + b[3] / 2
            return bx0 < a[0] < bx1 and by0 < a[1] < by1

        boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
        kept = []
        for b in boxes:
            if not any(_iou(b, k) > 0.15 or _inside(b, k) for k in kept):
                kept.append(b)
        # 2026-10-14 ROOT CAUSE FIX (user: at 00:32 the shot zoomed into a
        # character's hair): YuNet fired a 70x88px false positive ON THE
        # CURLY HAIR between two heads, and the dedupe kept it (IoU ~ 0 vs
        # the real face boxes, center not inside any box). The montage then
        # spent a whole solo segment zooming into hair. In a group portrait
        # every real face is roughly the same scale, so drop anything under
        # 25% of the largest box's area — self-calibrating, no hardcoded
        # pixel sizes. Cap at the 5 largest: intro holds max 5 people.
        if kept:
            max_area = max(b[2] * b[3] for b in kept)
            before = len(kept)
            kept = [b for b in kept if b[2] * b[3] >= 0.25 * max_area]
            dropped = before - len(kept)
            if dropped:
                print(f"[selfplug] dropped {dropped} micro-detection(s) "
                      f"<25% of largest face box area (false positives: hair/ears)")
            if len(kept) > 5:
                kept.sort(key=lambda b: b[2] * b[3], reverse=True)
                kept = kept[:5]
                print("[selfplug] capped at 5 faces (intro max 5 people)")
        return sorted(kept, key=lambda b: b[0])
    except Exception as e:
        print(f"[selfplug] face detection failed: {e}")
        return []


def closeup_box(cx, cy, sw, sh, n_people):
    """Close-up box centered on a face, exactly W:H aspect so no further
    cropping is needed — the person stays centered and fully in frame.
    Width is one person's share of the image; clamped to image bounds."""
    bw = sw / n_people
    bh = bw * H / W
    if bh > sh:
        bh = sh
        bw = bh * W / H
    x0 = min(max(cx - bw / 2, 0), sw - bw)
    y0 = min(max(cy - bh / 2, 0), sh - bh)
    return (x0, y0, x0 + bw, y0 + bh)


def main():
    src_path = ROOT / "cache" / "verified" / "intro_people.png"
    src = Image.open(src_path).convert("RGB")
    sw, sh = src.size

    faces = detect_faces(src_path)
    # 2026-10-23 (logo-pair montage): for a PORTRAIT source the characters
    # are stacked top-to-bottom in story order, so sort faces by y, not
    # by x. Left-to-right sorting on a vertical stack gives a scrambled
    # order (Dario, Zuckerberg, Altman, PHP, Jensen on the Oct 22 portrait)
    # and would pair every character with the wrong logo. Landscape keeps
    # the original left-to-right order.
    if sw < sh:
        faces = sorted(faces, key=lambda b: b[1])
    n = len(faces)
    if n == 0:
        print("[selfplug] WARNING: no faces detected in intro_people.png "
              "— falling back to a full-image slow push")
    else:
        print(f"[selfplug] detected {n} faces, close-up per person")
    boxes = [closeup_box(cx, cy, sw, sh, max(n, 1)) for cx, cy, _, _ in faces]
    # 2026-10-14: reviewable debug contact sheet — red = YuNet detection,
    # green = montage close-up box. Frame review can verify every box lands
    # on a face before the clip ships.
    try:
        from PIL import ImageDraw
        dbg = src.copy()
        dd = ImageDraw.Draw(dbg)
        for (cx, cy, w, h) in faces:
            dd.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                         outline=(255, 0, 0), width=5)
        for (x0, y0, x1, y1) in boxes:
            dd.rectangle([x0, y0, x1, y1], outline=(0, 255, 0), width=5)
        dbg.thumbnail((1080, 1080))
        dbg.save(ROOT / "cache" / "generated" / "selfplug_boxes.jpg")
    except Exception as e:
        print(f"[selfplug] debug sheet failed: {e}")

    # Logo per character (2026-10-23, user: logos right next to their
    # character): face i -> story_ids[i] -> story_icons[sid], if it is a
    # logo file that exists. Glyphs and missing files get no logo (the
    # pair falls back to a solo close-up), never a guessed logo.
    # Env overrides are for testing only (SELFPLUG_SCRIPT_JSON /
    # SELFPLUG_OUT); the daily worker runs with defaults.
    import json as _json, os as _os
    _script_path = _os.environ.get("SELFPLUG_SCRIPT_JSON") or str(
        ROOT / "output" / "script.json")
    # Logo/icon per story, in story order (2026-10-23 split montage):
    # ("file", path) for logo_*.png, ("glyph", name) for glyph:<name>,
    # None only when neither exists. Glyphs are drawn icons, not a
    # missing-logo fallback — the right side is company OR icon logos.
    _logos = []
    try:
        _sj = _json.loads(Path(_script_path).read_text())
        for _sid in _sj.get("story_ids", []):
            _ic = (_sj.get("story_icons") or {}).get(str(_sid), "")
            if _ic.startswith("logo_"):
                _lp = ROOT / "cache" / "verified" / _ic
                _logos.append(("file", str(_lp)) if _lp.exists() else None)
            elif _ic.startswith("glyph:"):
                _logos.append(("glyph", _ic[6:]))
            else:
                _logos.append(None)
    except Exception as e:
        print(f"[selfplug] logo map unavailable ({e}) — characters only")
    print(f"[selfplug] logos: {_logos}")

    def _logo_image(spec, max_w, max_h):
        """Logo/icon image for one right-side slot, or None."""
        from PIL import Image as _Im
        if spec is None:
            return None
        kind, val = spec
        if kind == "file":
            try:
                lg = _Im.open(val).convert("RGBA")
                lg.thumbnail((max_w, max_h), _Im.LANCZOS)
                return lg
            except Exception:
                return None
        # glyph: white line icon on black (draw_glyph returns RGB black bg)
        try:
            from visuals import draw_glyph as _dg
            g = _dg(val, S=140)
            if g is None:
                return None
            g = g.resize((min(max_w, max_h), min(max_w, max_h)), _Im.LANCZOS)
            return g.convert("RGBA")
        except Exception:
            return None

    def build_split(row_h):
        """Split composite: left = characters, right = logos/icons.
        One row per story, in story order, character crop on the left
        (680px wide, face-centred, with its relevant background) and
        its logo/icon centred on the right (400px wide). A thin divider
        separates the two sides."""
        from PIL import Image as _Im, ImageDraw as _Dr
        left_w, right_w = 680, 400
        comp = _Im.new("RGB", (W, row_h * max(1, len(faces))), (0, 0, 0))
        dr = _Dr.Draw(comp)
        dr.line([(left_w, 0), (left_w, comp.height)], fill=(60, 60, 60), width=3)
        for i, face in enumerate(faces):
            cx, cy, _, _ = face
            # Character crop (2026-10-23 fix): use ONLY this
            # character's own panel band (source height / n, in story
            # order), cropped to the left-panel aspect and centred on
            # the face horizontally. Square face crops pulled in the
            # neighbouring panel's torso, which showed as a duplicate
            # strip at row boundaries during the slide.
            panel_y0 = i * sh // max(1, len(faces))
            panel_y1 = (i + 1) * sh // max(1, len(faces))
            panel_h = panel_y1 - panel_y0
            cw = int(panel_h * left_w / row_h)
            x0 = int(min(max(cx - cw / 2, 0), sw - cw))
            char = src.crop((x0, panel_y0, x0 + cw, panel_y1)).resize(
                (left_w, row_h), _Im.LANCZOS)
            comp.paste(char, (0, i * row_h))
            spec = _logos[i] if i < len(_logos) else None
            lg = _logo_image(spec, right_w - 40, row_h - 40)
            if lg is not None:
                lx = left_w + (right_w - lg.width) // 2
                ly = i * row_h + (row_h - lg.height) // 2
                if lg.mode == "RGBA":
                    comp.paste(lg, (lx, ly), lg)
                else:
                    comp.paste(lg, (lx, ly))
        return comp

    # Slide composite: tall rows (560px each, 2800px total) that the
    # camera slides down over, top to bottom. Full composite: compact
    # rows (280px each, 1400px total) = the full split shot at the end.
    slide_comp = build_split(560) if faces else None
    full_comp = build_split(280) if faces else None
    print(f"[selfplug] split composites: slide {slide_comp.size if slide_comp else None}, full {full_comp.size if full_comp else None}")

    dest = _os.environ.get("SELFPLUG_OUT") or str(
        ROOT / "cache" / "generated" / "selfplug_pixar.mp4")
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(dest)]
    import subprocess
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

    # Timeline (2026-10-23 split montage): slide time = DUR - GROUP_DUR
    # slides top-to-bottom over the split composite; GROUP_DUR at the
    # end is the full split shot. With no faces, one full-image slow push.
    solo_total = DUR - GROUP_DUR
    if n == 0:
        segments = [(0.0, solo_total, -2), (solo_total, DUR, -1)]
    else:
        per = solo_total / n
        segments = [(i * per, (i + 1) * per, i) for i in range(n)]
        segments.append((solo_total, DUR, -1))

    total_frames = int(DUR * FPS)
    for i in range(total_frames):
        t = i / FPS
        seg_t, char_idx = 0.0, -1
        for s0, s1, ci in segments:
            if s0 <= t < s1:
                char_idx = ci
                seg_t = (t - s0) / max(0.001, (s1 - s0))
                break

        if char_idx == -1:
            # Full split shot (2026-10-23, user): all character+logo
            # pairs at once, left characters / right logos — NOT the
            # old portrait group, which has no logos on the right.
            frame = full_comp.copy() if full_comp is not None else _fit_group(src, faces)
        elif char_idx == -2:
            # No-face fallback: full-image slow push-in.
            z = 1.0 + 0.08 * ease_out(seg_t)
            zw, zh = sw / z, sh / z
            zx0, zy0 = (sw - zw) / 2, (sh - zh) / 2
            crop = src.crop((int(zx0), int(zy0),
                             int(zx0 + zw), int(zy0 + zh)))
            frame = _fit_exact(crop)
        else:
            # SPLIT MONTAGE (2026-10-23, user): the shot is split —
            # left side characters, right side company/icon logos.
            # The montage simply slides from top to bottom over the
            # tall split composite, then shows the full split shot.
            if slide_comp is not None and full_comp is not None:
                if t < solo_total:
                    prog = t / max(0.001, solo_total)
                    win_y = int(prog * (slide_comp.height - H))
                    frame = slide_comp.crop((0, win_y, W, win_y + H))
                else:
                    frame = full_comp.copy()
            else:
                frame = _fit_group(src, faces)
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"[selfplug] wrote {dest} ({DUR}s) - intro image emotion montage")


def _fit_exact(crop):
    """Box is already W:H aspect — straight resize, no cropping."""
    return crop.resize((W, H), Image.LANCZOS)


def _fit_group(crop, faces=None):
    """Group settle (2026-10-23, user: portrait original): if the source
    is PORTRAIT (aspect < 1, the new standard), use it DIRECTLY — fit
    it inside the 1080x1400 visual zone on a blurred background made
    from itself, so the whole portrait group stays visible with no
    cropping and no tile recomposition. The tile layout below is only
    for a legacy LANDSCAPE source (aspect >= 1), kept as a fallback.
    Portrait group (2026-10-23, user review fix): the landscape
    portrait (2480x992) pasted full-width into a portrait frame was a
    thin strip with blurred space above and below — it looked fitted
    for landscape, because it was. Now the group is RECOMPOSED for
    portrait: one large character on top, then a 2x2 grid of the other
    four, filling the whole 1080x1400 visual zone with no strip and no
    black padding. Each tile is a face-centred crop of its character
    (crop width capped at ~1.2x a character's share, so a neighbour's
    face never leaks into a tile). The background between tiles is
    RELEVANT, not black: the portrait itself, scaled to cover, heavily
    blurred and darkened, showing through the 10px gaps. With no faces
    detected, fall back to the old full-width fit."""
    from PIL import ImageEnhance, ImageFilter
    # Relevant background first: blurred portrait cover.
    s_bg = max(W / crop.width, H / crop.height)
    bg = crop.resize((max(1, int(crop.width * s_bg)),
                      max(1, int(crop.height * s_bg))), Image.LANCZOS)
    bx = (bg.width - W) // 2
    by = (bg.height - H) // 2
    bg = bg.crop((bx, by, bx + W, by + H))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
    bg = ImageEnhance.Brightness(bg).enhance(0.70)
    if crop.width < crop.height:
        # Portrait source: fit the whole group inside the visual zone.
        s = min(W / crop.width, H / crop.height)
        nw, nh = int(crop.width * s), int(crop.height * s)
        fitted = crop.resize((nw, nh), Image.LANCZOS)
        bg.paste(fitted, ((W - nw) // 2, (H - nh) // 2))
        return bg
    if not faces:
        scale = W / crop.width
        new_h = int(crop.height * scale)
        resized = crop.resize((W, new_h), Image.LANCZOS)
        bg.paste(resized, (0, (H - new_h) // 2))
        return bg
    # Tile layout: top 1080x560, then 2 rows of 535x410, 10px gaps.
    # 560 + 10 + 410 + 10 + 410 = 1400.
    tiles = [(0, 0, 1080, 560)]
    for r in range(2):
        y0 = 570 + r * 420
        tiles.append((0, y0, 535, 410))
        tiles.append((545, y0, 535, 410))
    sw, sh = crop.size
    share = sw / max(len(faces), 1)
    for (tx, ty, tw, th), (fcx, fcy, fw, fh) in zip(
            tiles, faces[:5]):
        tile_aspect = tw / th
        cw = min(int(share * 1.0), sw)
        ch = int(cw / tile_aspect)
        if ch > sh:
            ch = sh
            cw = int(ch * tile_aspect)
        x0 = int(min(max(fcx - cw / 2, 0), sw - cw))
        # Face sits in the upper third of its tile, torso below.
        y0 = int(min(max(fcy - ch * 0.35, 0), sh - ch))
        tile = crop.crop((x0, y0, x0 + cw, y0 + ch))
        tile = tile.resize((tw, th), Image.LANCZOS)
        bg.paste(tile, (tx, ty))
    return bg


if __name__ == "__main__":
    main()
