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
W, H, FPS = 1080, 1220, 30
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
    n = len(faces)
    if n == 0:
        print("[selfplug] WARNING: no faces detected in intro_people.png "
              "— falling back to a full-image slow push")
    else:
        print(f"[selfplug] detected {n} faces, close-up per person")
    boxes = [closeup_box(cx, cy, sw, sh, max(n, 1)) for cx, cy, _, _ in faces]

    dest = ROOT / "cache" / "generated" / "selfplug_pixar.mp4"
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(dest)]
    import subprocess
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

    # Timeline: solo time splits evenly across the detected people, then
    # the group settle. With no faces, one full-image slow push instead.
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
            # Full group shot — fit entire width with black padding,
            # never crop characters off the edges.
            crop = src
            frame = _fit_group(crop)
        elif char_idx == -2:
            # No-face fallback: full-image slow push-in.
            z = 1.0 + 0.08 * ease_out(seg_t)
            zw, zh = sw / z, sh / z
            zx0, zy0 = (sw - zw) / 2, (sh - zh) / 2
            crop = src.crop((int(zx0), int(zy0),
                             int(zx0 + zw), int(zy0 + zh)))
            frame = _fit_exact(crop)
        else:
            # Individual close-up: gentle push-in on the face-centered box.
            x0, y0, x1, y1 = boxes[char_idx]
            bw, bh = x1 - x0, y1 - y0
            z = 1.0 + 0.12 * ease_out(seg_t)
            zw, zh = bw / z, bh / z
            cx, cy = x0 + bw / 2, y0 + bh / 2
            zx0 = min(max(cx - zw / 2, 0), sw - zw)
            zy0 = min(max(cy - zh / 2, 0), sh - zh)
            crop = src.crop((int(zx0), int(zy0),
                             int(zx0 + zw), int(zy0 + zh)))
            frame = _fit_exact(crop)
        proc.stdin.write(frame.tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"[selfplug] wrote {dest} ({DUR}s) - intro image emotion montage")


def _fit_exact(crop):
    """Box is already W:H aspect — straight resize, no cropping."""
    return crop.resize((W, H), Image.LANCZOS)


def _fit_group(crop):
    """Group: fit width, pad vertically with black."""
    scale = W / crop.width
    new_h = int(crop.height * scale)
    resized = crop.resize((W, new_h), Image.LANCZOS)
    frame = Image.new("RGB", (W, H), (0, 0, 0))
    frame.paste(resized, (0, (H - new_h) // 2))
    return frame


if __name__ == "__main__":
    main()
