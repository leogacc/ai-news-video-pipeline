#!/usr/bin/env python3
"""Self-plug animated clip (2026-10-09): terminal-style motion graphic for
story 1 (OpenAI fires safety researchers). Neon green on black, 1080x1220
(shot region), 30fps. Replaces the static YouTube card."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, FPS = 1080, 1220, 30
DUR = 6.0
NEON = (57, 255, 20)
RED = (255, 60, 60)
DIM = (0, 90, 20)

def _font(sz):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", sz)
    except Exception:
        return ImageFont.load_default()

def main():
    n = int(DUR * FPS)
    f_big = _font(64)
    f_mid = _font(48)
    # OpenAI blossom for the header
    try:
        logo = Image.open(ROOT / "cache" / "verified" / "logo_openai.png"
                          ).convert("RGB").resize((120, 120), Image.LANCZOS)
    except Exception:
        logo = None

    out_dir = ROOT / "cache" / "generated"
    out_dir.mkdir(exist_ok=True)
    dest = out_dir / "selfplug_story1.mp4"

    # Build frames via ffmpeg raw pipe
    import subprocess
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           str(dest)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    line1 = "OPENAI FIRES"
    line2 = "SAFETY TEAM"
    line3 = "3 RESEARCHERS OUT"

    for i in range(n):
        t = i / FPS
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)

        # Logo fades in 0-0.8s, pulses subtly
        if logo is not None:
            a = min(1.0, t / 0.8)
            pulse = 1.0 + 0.03 * math.sin(t * 4)
            ls = int(120 * pulse)
            lg = logo.resize((ls, ls), Image.LANCZOS)
            black = Image.new("RGB", lg.size, (0, 0, 0))
            lx = (W - ls) // 2
            img.paste(Image.blend(black, lg, a), (lx, 120))

        # Line 1 types 0.8-2.0s
        if t > 0.8:
            k = int(min(len(line1), (t - 0.8) / 1.2 * len(line1)))
            s = "> " + line1[:k]
            if k < len(line1):
                s += "█"
            tw = meas.textlength(s, font=f_big)
            d.text(((W - tw) / 2, 300), s, font=f_big, fill=NEON)

        # Line 2 types 2.0-3.2s
        if t > 2.0:
            k = int(min(len(line2), (t - 2.0) / 1.2 * len(line2)))
            s = "> " + line2[:k]
            if k < len(line2):
                s += "█"
            tw = meas.textlength(s, font=f_big)
            d.text(((W - tw) / 2, 400), s, font=f_big, fill=NEON)

        # Line 3 (red) types 3.2-4.4s, then three X marks stamp in
        if t > 3.2:
            k = int(min(len(line3), (t - 3.2) / 1.2 * len(line3)))
            s = "> " + line3[:k]
            if k < len(line3):
                s += "█"
            tw = meas.textlength(s, font=f_mid)
            d.text(((W - tw) / 2, 560), s, font=f_mid, fill=RED)

        # Three figure icons get X'd out 4.4-5.6s
        if t > 4.4:
            for j in range(3):
                jt = t - 4.4 - j * 0.35
                if jt <= 0:
                    continue
                cx = W // 2 + (j - 1) * 220
                cy = 800
                # person glyph (circle head + body)
                d.ellipse([cx - 40, cy - 90, cx + 40, cy - 10], outline=DIM,
                          width=6)
                d.arc([cx - 60, cy - 40, cx + 60, cy + 120], 180, 360,
                      fill=DIM, width=6)
                # red X stamps in with overshoot
                xp = min(1.0, jt / 0.3)
                xe = 1 + 2.2 * (xp - 1) ** 3 + 1.2 * (xp - 1) ** 2 if xp < 1 else 1
                r = int(90 * max(0.01, xe))
                d.line([cx - r, cy - r, cx + r, cy + r], fill=RED, width=10)
                d.line([cx - r, cy + r, cx + r, cy - r], fill=RED, width=10)

        # "LINK IN BIO" fades in at the end
        if t > 5.0:
            a = min(1.0, (t - 5.0) / 0.6)
            s = "LINK IN BIO"
            tw = meas.textlength(s, font=f_mid)
            # manual alpha via blend
            ov = Image.new("RGB", (W, H), (0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.text(((W - tw) / 2, 1050), s, font=f_mid, fill=NEON)
            img = Image.blend(img, Image.composite(ov, img, ov.convert("L").point(lambda v: int(v * a))), a)

        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    print(f"[selfplug] wrote {dest} ({DUR}s)")

if __name__ == "__main__":
    main()
