#!/usr/bin/env python3
"""Analytical animations (2026-10-09): terminal-aesthetic motion graphics
for number-heavy stories. Neon green on black, 1080x1220 (shot region).

The animation-tools report ranked Manim #1 for diagram work, but Manim's
Cairo/Pango/LaTeX stack is too heavy for this VM (1.5GB free). This module
produces the same analytical look (animated bars, counters, charts) with
PIL frames -> ffmpeg, matching the channel's terminal aesthetic.

Clips are generated once and pinned to cache/generated/; the pipeline
maps number-heavy shots to them.
"""
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, FPS = 1080, 1220, 30
NEON = (57, 255, 20)
RED = (255, 70, 70)
DIM = (0, 80, 16)
GRAY = (120, 140, 120)

GEN_DIR = ROOT / "cache" / "generated"
GEN_DIR.mkdir(exist_ok=True)


def _font(sz):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def _write(frames_iter, n, dest):
    # 2026-10-11: explicit BT.709 colorspace — without metadata ffmpeg
    # guesses the matrix differently on encode vs decode, shifting chroma
    # and tinting pure black (green hue). out_color_matrix forces BT.709
    # for the RGB->YUV conversion; the tags ensure correct decode.
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-vf", "scale=out_color_matrix=bt709",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
           "-colorspace", "bt709", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-color_range", "tv",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(dest)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    for img in frames_iter(n):
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"[analytics] wrote {dest.name}")


def _ease(x):
    # snappy ease-out with slight overshoot — for GEOMETRY (bars, lines)
    # only. Never drive a displayed number with this: the overshoot puts
    # a wrong digit on screen (chart-animation skill: a wrong digit is
    # not forgivable, a one-pixel layout bug is).
    x = max(0.0, min(1.0, x))
    return 1 + 2.0 * (x - 1) ** 3 + 1.0 * (x - 1) ** 2


def _ease_out_cubic(x):
    # monotonic ease for DISPLAYED NUMBERS — settles on the exact value,
    # never overshoots past it.
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def genesis_pledges(dur=6.0):
    """Animated bar chart: Genesis Mission $2.4B pledge breakdown.
    Nvidia $1B, AMD $500M, OpenAI $200M, Total $2.4B."""
    dest = GEN_DIR / "analytics_genesis_pledges.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_num = _font(52)
    bars = [
        ("NVIDIA", 1.0, "$1.0B"),
        ("AMD", 0.5, "$500M"),
        ("OPENAI", 0.2, "$200M"),
        ("TOTAL", 2.4, "$2.4B"),
    ]
    maxv = 2.4
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            # Title types in
            title = "GENESIS PLEDGES"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            # Bars grow sequentially
            y0 = 260
            for bi, (name, val, txt) in enumerate(bars):
                bt = t - 0.8 - bi * 0.7
                if bt <= 0:
                    continue
                p = _ease(bt / 0.9)
                bw = int(760 * (val / maxv) * p)
                y = y0 + bi * 200
                # label
                d.text((80, y), name, font=f_label, fill=GRAY)
                # bar track
                d.rectangle([80, y + 70, 840, y + 120], fill=(10, 20, 12))
                # bar fill
                col = NEON if name != "TOTAL" else (57, 255, 20)
                if bw > 0:
                    d.rectangle([80, y + 70, 80 + bw, y + 120], fill=col)
                # value counts up with the bar — real intermediate values in the
                # bar's own unit (chart-animation: ease the VALUE). Shown from
                # p>0.1; exact final string at p>=1 so the settled digit is
                # always the true fact.
                if p > 0.1:
                    if p >= 1:
                        vtxt = txt
                    elif val >= 1:
                        vtxt = f"${val * p:.1f}B"
                    else:
                        vtxt = f"${val * p * 1000:.0f}M"
                    d.text((860, y + 60), vtxt, font=f_num, fill=NEON)
                # total gets a highlight (box sized to not clip the value text)
                if name == "TOTAL" and p >= 1:
                    d.rectangle([70, y - 10, 1030, y + 140], outline=NEON,
                                width=3)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest




def revenue_selloff(dur=6.0):
    """Animated counter: $50B revenue miss with red down arrow.
    Counts $0 -> $50B, then '$20B BELOW EXPECTED' stamps in."""
    dest = GEN_DIR / "analytics_revenue_selloff.mp4"
    f_big = _font(110)
    f_mid = _font(48)
    f_small = _font(40)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    # Center the counter on its FINAL width (monospace, but digit count
    # changes as it rolls: "$9.9B" -> "$50.0B") so it never jumps sideways.
    _final_w = meas.textlength("$50.0B", font=f_big)

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            # Title
            title = "REVENUE MISS"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            # Counter $0 -> $50B over 2.5s, monotonic ease — the displayed
            # digit never overshoots past the true $50B (chart-animation).
            ct = min(1.0, max(0.0, (t - 0.8) / 2.5))
            ce = _ease_out_cubic(ct)
            val = 50 * ce
            s = f"${val:.1f}B"
            d.text(((W - _final_w) / 2, 300), s, font=f_big, fill=NEON)
            # Red down arrow draws 3.3-4.3s
            at = t - 3.3
            if at > 0:
                ap = min(1.0, at / 1.0)
                # arrow shaft
                x0, y0, y1 = W // 2, 520, 520 + int(300 * ap)
                d.line([x0, y0, x0, y1], fill=RED, width=18)
                if ap > 0.7:
                    hp = (ap - 0.7) / 0.3
                    hr = int(70 * hp)
                    d.line([x0 - hr, y1 - hr, x0, y1], fill=RED, width=18)
                    d.line([x0 + hr, y1 - hr, x0, y1], fill=RED, width=18)
            # "$20B BELOW EXPECTED" + "-1.3% NASDAQ" stamp in — FULL opacity,
            # no fade (2026-10-10: user said nothing transparent in animations)
            if t > 4.3:
                col = (255, 70, 70)
                s2 = "$20B BELOW EXPECTED"
                tw2 = meas.textlength(s2, font=f_mid)
                d.text(((W - tw2) / 2, 900), s2, font=f_mid, fill=col)
                s3 = "NASDAQ -1.3%"
                tw3 = meas.textlength(s3, font=f_small)
                d.text(((W - tw3) / 2, 990), s3, font=f_small,
                       fill=(200, 60, 60))
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def state_of_ai(dur=6.0):
    """Animated bar chart: OpenAI+Anthropic combined annualized run rate
    $30B (January) -> $105B (late summer), per State of AI Report 2026.
    Kicker: benchmark scores 13x cheaper every year since 2023."""
    dest = GEN_DIR / "analytics_state_of_ai.mp4"
    f_mid = _font(48)
    f_label = _font(44)
    f_num = _font(60)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    bars = [
        ("JAN", 30, "$30B"),
        ("LATE SUMMER", 105, "$105B"),
    ]
    maxv = 105

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            # Title types in
            title = "COMBINED RUN RATE"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            sub = "OPENAI + ANTHROPIC"
            if t > 0.5:
                d.text((80, 160), sub, font=f_label, fill=GRAY)
            # Bars grow with snappy ease, staggered
            bw, gap, base_y = 300, 120, 900
            x0 = (W - (2 * bw + gap)) // 2
            for j, (label, val, tag) in enumerate(bars):
                bt = max(0.0, (t - 0.8 - j * 0.5) / 1.2)
                be = _ease(bt)
                bh = int(620 * (val / maxv) * be)
                x = x0 + j * (bw + gap)
                if bh > 0:
                    col = NEON if j == 1 else DIM
                    d.rectangle([x, base_y - bh, x + bw, base_y], fill=col)
                if bt > 0.15:
                    tw = meas.textlength(label, font=f_label)
                    d.text((x + (bw - tw) / 2, base_y + 24), label,
                           font=f_label, fill=GRAY)
                    tw2 = meas.textlength(tag, font=f_num)
                    d.text((x + (bw - tw2) / 2, base_y - bh - 84), tag,
                           font=f_num, fill=NEON)
            # "13x CHEAPER / YEAR" stamps in — full opacity, no fade
            if t > 3.6:
                s2 = "13x CHEAPER / YEAR"
                tw3 = meas.textlength(s2, font=f_mid)
                d.text(((W - tw3) / 2, 1020), s2, font=f_mid, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def cost_curve(dur=6.0):
    """Animated falling line chart: benchmark cost 13x cheaper yearly.
    Neon green line on black, falling from top-left to bottom-right.
    For 'benchmark scores got thirteen times cheaper yearly' shots."""
    dest = GEN_DIR / "analytics_cost_curve.mp4"
    f_mid = _font(48)
    f_label = _font(44)
    f_num = _font(60)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            # Title types in
            title = "BENCHMARK COST"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            sub = "13x CHEAPER EVERY YEAR"
            if t > 0.5:
                k2 = int(min(len(sub), (t - 0.5) / 0.8 * len(sub)))
                d.text((80, 160), sub[:k2], font=f_label, fill=GRAY)
            # Falling line chart: exponential decay
            # Chart area
            cx0, cy0 = 120, 300  # top-left of chart
            cw, ch = W - 240, 600  # chart width/height
            # Draw axes
            d.line([cx0, cy0, cx0, cy0 + ch], fill=(60, 60, 60), width=3)
            d.line([cx0, cy0 + ch, cx0 + cw, cy0 + ch], fill=(60, 60, 60), width=3)
            # Animate line drawing (progress 0->1 over 2 seconds)
            prog = max(0.0, min(1.0, (t - 1.0) / 2.0))
            prog = _ease(prog)
            if prog > 0:
                pts = []
                n_pts = int(50 * prog) + 1
                for j in range(n_pts):
                    x = cx0 + (j / 49) * cw
                    # Exponential decay: cost falls 13x per year
                    # y = ch * (1 - exp decay)
                    decay = 0.92 ** (j / 49 * 20)  # steep fall
                    y = cy0 + ch * (1 - decay * 0.9)
                    pts.append((x, y))
                if len(pts) > 1:
                    d.line(pts, fill=NEON, width=6, joint="curve")
                    # Dot at the end
                    d.ellipse([pts[-1][0]-12, pts[-1][1]-12,
                               pts[-1][0]+12, pts[-1][1]+12], fill=NEON)
            # Year labels
            if t > 1.5:
                d.text((cx0, cy0 + ch + 20), "2023", font=f_label, fill=GRAY)
                tw = meas.textlength("2026", font=f_label)
                d.text((cx0 + cw - tw, cy0 + ch + 20), "2026",
                       font=f_label, fill=GRAY)
            # "13x" stamp
            if t > 3.2:
                s = "13x CHEAPER"
                tw2 = meas.textlength(s, font=f_num)
                d.text(((W - tw2) / 2, 1020), s, font=f_num, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def samsung_profit(dur=6.0):
    """Animated bar chart: biggest quarterly tech profit ever.
    Samsung $80.2B (Q3 2026) vs Nvidia $63.7B (previous record).
    Displayed numbers use monotonic ease — never overshoot the fact."""
    dest = GEN_DIR / "analytics_samsung_profit.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_num = _font(60)
    bars = [
        ("NVIDIA", 63.7, "$63.7B"),
        ("SAMSUNG", 80.2, "$80.2B"),
    ]
    maxv = 80.2
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            # Title types in
            title = "BIGGEST TECH QUARTER EVER"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            sub = "Q3 OPERATING PROFIT"
            if t > 0.5:
                d.text((80, 160), sub, font=f_label, fill=GRAY)
            # Bars grow with snappy ease, staggered; numbers count
            # monotonically to the exact fact
            bw, gap, base_y = 300, 120, 900
            x0 = (W - (2 * bw + gap)) // 2
            for j, (label, val, tag) in enumerate(bars):
                bt = max(0.0, (t - 0.8 - j * 0.5) / 1.2)
                be = _ease(bt)            # geometry may overshoot
                ne = _ease_out_cubic(bt)  # digits never do
                bh = int(620 * (val / maxv) * be)
                x = x0 + j * (bw + gap)
                if bh > 0:
                    col = NEON if j == 1 else DIM
                    d.rectangle([x, base_y - bh, x + bw, base_y], fill=col)
                if bt > 0.15:
                    tw = meas.textlength(label, font=f_label)
                    d.text((x + (bw - tw) / 2, base_y + 24), label,
                           font=f_label, fill=GRAY)
                    shown = tag if ne >= 1 else f"${val * ne:.1f}B"
                    tw2 = meas.textlength(tag, font=f_num)
                    d.text((x + (bw - tw2) / 2, base_y - bh - 84), shown,
                           font=f_num, fill=NEON)
            # "UP 9X IN A YEAR" stamps in — full opacity, no fade
            if t > 3.6:
                s2 = "UP 9x IN A YEAR"
                tw3 = meas.textlength(s2, font=f_title)
                d.text(((W - tw3) / 2, 1020), s2, font=f_title, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def broadcom_outlook(dur=6.0):
    """Animated bar chart: Broadcom AI chip outlook vs Anthropic loan.
    $115B FY2027 AI chip revenue outlook vs $42B committed Anthropic loan.
    Displayed numbers use monotonic ease — never overshoot the fact."""
    dest = GEN_DIR / "analytics_broadcom_outlook.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_num = _font(60)
    bars = [
        ("ANTHROPIC LOAN", 42.0, "$42B"),
        ("AI CHIP OUTLOOK", 115.0, "$115B"),
    ]
    maxv = 115.0
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            # Title types in
            title = "CAPITAL, NOT CHIPS"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            sub = "BROADCOM FY2027 ($B)"
            if t > 0.5:
                d.text((80, 160), sub, font=f_label, fill=GRAY)
            # Bars grow with snappy ease, staggered; numbers count
            # monotonically to the exact fact
            bw, gap, base_y = 300, 120, 900
            x0 = (W - (2 * bw + gap)) // 2
            for j, (label, val, tag) in enumerate(bars):
                bt = max(0.0, (t - 0.8 - j * 0.5) / 1.2)
                be = _ease(bt)            # geometry may overshoot
                ne = _ease_out_cubic(bt)  # digits never do
                bh = int(620 * (val / maxv) * be)
                x = x0 + j * (bw + gap)
                if bh > 0:
                    col = NEON if j == 1 else DIM
                    d.rectangle([x, base_y - bh, x + bw, base_y], fill=col)
                if bt > 0.15:
                    tw = meas.textlength(label, font=f_label)
                    d.text((x + (bw - tw) / 2, base_y + 24), label,
                           font=f_label, fill=GRAY)
                    shown = tag if ne >= 1 else f"${val * ne:.0f}B"
                    tw2 = meas.textlength(tag, font=f_num)
                    d.text((x + (bw - tw2) / 2, base_y - bh - 84), shown,
                           font=f_num, fill=NEON)
            # "2.7x THE LOAN" stamps in — full opacity, no fade
            if t > 3.6:
                s2 = "OUTLOOK IS 2.7x THE LOAN"
                tw3 = meas.textlength(s2, font=f_title)
                d.text(((W - tw3) / 2, 1020), s2, font=f_title, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


if __name__ == "__main__":
    genesis_pledges()
    revenue_selloff()
    state_of_ai()
    cost_curve()
    samsung_profit()
    broadcom_outlook()
