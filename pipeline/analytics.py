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
import numpy as np

# 2026-10-14 CAPTION-SAFE RULE (user: analytical red text overlapped the
# captions at 1:40). Analytical clips are padded at frame y=290 in
# render.py; the typewriter captions' wrapped line-1 tops sit at about
# frame y=1430. No analytics text may be drawn at/below clip row 1090
# (frame y 1380) — 50px of clearance. _write enforces this on every
# generated clip and FAILS LOUD, so future generators can't regress it.
CAPTION_SAFE_BOTTOM = 1090

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
    for fi, img in enumerate(frames_iter(n)):
        # 2026-10-14: caption-safe guard — every 6th frame, fail loud if
        # any non-black pixel is drawn at/below CAPTION_SAFE_BOTTOM.
        if fi % 6 == 0:
            band = np.asarray(img.crop((0, CAPTION_SAFE_BOTTOM, W, H)))
            if (band > 24).any():
                proc.stdin.close()
                proc.wait()
                raise RuntimeError(
                    f"[analytics] FATAL: {dest.name} draws below "
                    f"caption-safe row {CAPTION_SAFE_BOTTOM} — move the "
                    f"text up (see CAPTION_SAFE_BOTTOM rule)")
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


def muse_wonder_benchmark(dur=6.0):
    """Animated bar chart: Artificial Analysis Intelligence Index.
    Opus 5.5 (58), Wonder Full (56), Wonder (52). Displayed numbers use
    monotonic ease — never overshoot the fact."""
    dest = GEN_DIR / "analytics_muse_wonder_benchmark.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_num = _font(60)
    bars = [
        ("WONDER", 52, "52"),
        ("WONDER FULL", 56, "56"),
        ("OPUS 5.5", 58, "58"),
    ]
    maxv = 58
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "FRONTIER BENCHMARK"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            sub = "ARTIFICIAL ANALYSIS INDEX"
            if t > 0.5:
                d.text((80, 160), sub, font=f_label, fill=GRAY)
            bw, gap, base_y = 260, 60, 900
            x0 = (W - (3 * bw + 2 * gap)) // 2
            for j, (label, val, tag) in enumerate(bars):
                bt = max(0.0, (t - 0.8 - j * 0.5) / 1.2)
                be = _ease(bt)
                ne = _ease_out_cubic(bt)
                bh = int(620 * (val / maxv) * be)
                x = x0 + j * (bw + gap)
                if bh > 0:
                    col = NEON if j == 1 else DIM
                    d.rectangle([x, base_y - bh, x + bw, base_y], fill=col)
                if bt > 0.15:
                    tw = meas.textlength(label, font=f_label)
                    d.text((x + (bw - tw) / 2, base_y + 24), label,
                           font=f_label, fill=GRAY)
                    shown = tag if ne >= 1 else f"{val * ne:.0f}"
                    tw2 = meas.textlength(tag, font=f_num)
                    d.text((x + (bw - tw2) / 2, base_y - bh - 84), shown,
                           font=f_num, fill=NEON)
            if t > 3.9:
                s2 = "2 POINTS OFF THE TOP"
                tw3 = meas.textlength(s2, font=f_title)
                d.text(((W - tw3) / 2, 1020), s2, font=f_title, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def maia_300_specs(dur=6.0):
    """Animated counters: Maia 300 headline specs. 40% more tokens per
    megawatt, 96 chips per rack, 7x rack throughput vs Maia 200.
    Displayed numbers use monotonic ease — never overshoot the fact."""
    dest = GEN_DIR / "analytics_maia_300_specs.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_big = _font(110)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("40%", 40, "{:.0f}%", "MORE TOKENS PER MEGAWATT"),
        ("96", 96, "{:.0f}", "CHIPS PER RACK"),
        ("7x", 7, "{:.0f}x", "RACK THROUGHPUT VS MAIA 200"),
    ]
    finals = [meas.textlength(tag, font=f_big) for tag, _, _, _ in rows]

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "MAIA 300"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            y0 = 300
            for ri, (tag, val, fmt, label) in enumerate(rows):
                rt = t - 0.8 - ri * 0.9
                if rt <= 0:
                    continue
                ne = _ease_out_cubic(min(1.0, rt / 1.4))
                shown = tag if ne >= 1 else fmt.format(val * ne)
                y = y0 + ri * 300
                d.text(((W - finals[ri]) / 2, y), shown, font=f_big,
                       fill=NEON)
                lw = meas.textlength(label, font=f_label)
                d.text(((W - lw) / 2, y + 150), label, font=f_label,
                       fill=GRAY)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def ai_oversight_letter(dur=6.0):
    """Animated counters: the scientists' open letter by the numbers.
    400 scientists, 34 countries — then the AIR-GAP demand stamps in."""
    dest = GEN_DIR / "analytics_ai_oversight_letter.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_big = _font(110)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("400", 400, "{:.0f}", "SCIENTISTS SIGN THE LETTER"),
        ("34", 34, "{:.0f}", "COUNTRIES"),
    ]
    finals = [meas.textlength(tag, font=f_big) for tag, _, _, _ in rows]

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "THE LETTER"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            y0 = 280
            for ri, (tag, val, fmt, label) in enumerate(rows):
                rt = t - 0.8 - ri * 0.9
                if rt <= 0:
                    continue
                ne = _ease_out_cubic(min(1.0, rt / 1.4))
                shown = tag if ne >= 1 else fmt.format(val * ne)
                y = y0 + ri * 300
                d.text(((W - finals[ri]) / 2, y), shown, font=f_big,
                       fill=NEON)
                lw = meas.textlength(label, font=f_label)
                d.text(((W - lw) / 2, y + 150), label, font=f_label,
                       fill=GRAY)
            # The demand stamps in — full opacity, no fade
            if t > 3.6:
                s2 = "AIR-GAP THE MODELS"
                tw = meas.textlength(s2, font=f_title)
                d.text(((W - tw) / 2, 980), s2, font=f_title, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def asia_selloff(dur=6.0):
    """Animated falling bars: Tuesday's Asia AI selloff in red.
    KOSPI -6%, Kioxia -13%, Samsung -10%, SK Hynix -8%.
    Displayed numbers count down monotonically — never overshoot."""
    dest = GEN_DIR / "analytics_asia_selloff.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_num = _font(52)
    bars = [
        ("KOSPI", 6, "-6%"),
        ("KIOXIA", 13, "-13%"),
        ("SAMSUNG", 10, "-10%"),
        ("SK HYNIX", 8, "-8%"),
    ]
    maxv = 13
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "AI SELLOFF"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=RED)
            sub = "ASIA, TUESDAY"
            if t > 0.5:
                d.text((80, 160), sub, font=f_label, fill=GRAY)
            y0 = 280
            for bi, (name, val, txt) in enumerate(bars):
                bt = t - 0.8 - bi * 0.6
                if bt <= 0:
                    continue
                p = _ease(bt / 0.8)
                bw = int(700 * (val / maxv) * p)
                y = y0 + bi * 210
                d.text((80, y), name, font=f_label, fill=GRAY)
                d.rectangle([80, y + 70, 780, y + 120], fill=(24, 8, 8))
                if bw > 0:
                    d.rectangle([80, y + 70, 80 + bw, y + 120], fill=RED)
                if p > 0.1:
                    ne = _ease_out_cubic(min(1.0, bt / 0.8))
                    shown = txt if ne >= 1 else f"-{val * ne:.0f}%"
                    d.text((810, y + 60), shown, font=f_num, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def imf_warning(dur=6.0):
    """Animated counters: the IMF's AI-stability warning by the numbers.
    $1.4T in future revenue commitments, 10% of investment-grade bond
    issuance, -1.1% global GDP in the downside scenario."""
    dest = GEN_DIR / "analytics_imf_warning.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_big = _font(100)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("$1.4T", 1.4, "${:.1f}T", "FUTURE REVENUE COMMITMENTS", NEON),
        ("10%", 10, "{:.0f}%", "OF INVESTMENT-GRADE BOND ISSUANCE", NEON),
        ("-1.1%", 1.1, "-{:.1f}%", "GLOBAL GDP: DOWNSIDE SCENARIO", RED),
    ]
    finals = [meas.textlength(tag, font=f_big) for tag, _, _, _, _ in rows]

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "IMF WARNING"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            y0 = 280
            for ri, (tag, val, fmt, label, col) in enumerate(rows):
                rt = t - 0.8 - ri * 0.9
                if rt <= 0:
                    continue
                ne = _ease_out_cubic(min(1.0, rt / 1.4))
                shown = tag if ne >= 1 else fmt.format(val * ne)
                y = y0 + ri * 300
                d.text(((W - finals[ri]) / 2, y), shown, font=f_big,
                       fill=col)
                lw = meas.textlength(label, font=f_label)
                d.text(((W - lw) / 2, y + 140), label, font=f_label,
                       fill=GRAY)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def asml_record_quarter(dur=6.0):
    """Animated counters: ASML's record Q3 2026.
    EUR 11.7B sales, EUR 5.0B net income, 57.5% gross margin (company
    record) - and planned 2027-2028 supply that cannot meet demand."""
    dest = GEN_DIR / "analytics_asml_record_quarter.mp4"
    f_title = _font(56)
    f_label = _font(40)
    f_big = _font(100)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("11.7", 11.7, "{:.1f}", "BILLION EUROS NET SALES", NEON),
        ("5.0", 5.0, "{:.1f}", "BILLION EUROS NET INCOME", NEON),
        ("57.5%", 57.5, "{:.1f}%", "GROSS MARGIN - COMPANY RECORD", NEON),
    ]
    finals = [meas.textlength(tag, font=f_big) for tag, _, _, _, _ in rows]

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "ASML Q3 RECORD"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            # 2026-10-14: row pitch was 280, which pushed the footer kicker
            # to clip y 1180 (frame y 1470) — inside the caption band, so it
            # overlapped the typewriter captions (user report 1:40). Rows
            # re-spaced to 240; the footer now sits at clip y 1000
            # (frame y 1290), above CAPTION_SAFE_BOTTOM.
            y0, pitch = 300, 240
            for ri, (tag, val, fmt, label, col) in enumerate(rows):
                rt = t - 0.8 - ri * 0.9
                if rt <= 0:
                    continue
                ne = _ease_out_cubic(min(1.0, rt / 1.4))
                shown = tag if ne >= 1 else fmt.format(val * ne)
                y = y0 + ri * pitch
                d.text(((W - finals[ri]) / 2, y), shown, font=f_big,
                       fill=col)
                lw = meas.textlength(label, font=f_label)
                d.text(((W - lw) / 2, y + 140), label, font=f_label,
                       fill=GRAY)
            # footer kicker once numbers settle
            if t > 3.6:
                fk = "SOLD OUT THROUGH 2028"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 1000), fk,
                       font=f_label, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest




def ai_rout_drops(dur=6.0):
    """Animated bars: AI-stock rout 2026-10-15.
    CoreWeave -15%, Oracle -9%, Micron -4%, AMD -1.9%, Nvidia -1.3%;
    $80B wiped in a single day; Nasdaq 100 futures -1.26%."""
    dest = GEN_DIR / "analytics_ai_rout_drops.mp4"
    f_title = _font(56)
    f_label = _font(34)
    f_val = _font(48)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("COREWEAVE", 15.0, "-15%"),
        ("ORACLE", 9.0, "-9%"),
        ("MICRON", 4.0, "-4%"),
        ("AMD", 1.9, "-1.9%"),
        ("NVIDIA", 1.3, "-1.3%"),
    ]
    maxv = 15.0
    base_x, max_len = 990, 780

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "AI ROUT DEEPENS"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            y0, pitch = 250, 130
            for ri, (name, val, tag) in enumerate(rows):
                rt = t - 0.8 - ri * 0.55
                if rt <= 0:
                    continue
                y = y0 + ri * pitch
                nlw = meas.textlength(name, font=f_label)
                d.text((90, y), name, font=f_label, fill=GRAY)
                # bar grows leftward from the right baseline (drops)
                ge = _ease(min(1.0, rt / 0.9))
                ln = int(max_len * (val / maxv) * ge)
                d.line([(base_x - ln, y + 52), (base_x, y + 52)],
                       fill=RED, width=34)
                # displayed number: monotonic ease, settles exact
                ne = _ease_out_cubic(min(1.0, rt / 1.1))
                shown = tag if ne >= 1 else "-{:.1f}%".format(val * ne)
                vw = meas.textlength(shown, font=f_val)
                d.text((base_x - ln - vw - 24, y + 28), shown,
                       font=f_val, fill=NEON)
            # footer kicker once bars settle (clip y 960 < 1090 safe)
            if t > 3.4:
                fk = "$80B WIPED IN A DAY"
                flw = meas.textlength(fk, font=f_val)
                d.text(((W - flw) / 2, 960), fk, font=f_val, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def certin_attack_timeline(dur=6.0):
    """Attack compression: CERT-In 2026-10-16.
    Criminals using open agentic AI tools squeezed intrusions that took
    DAYS down to a few HOURS. Two bars visualize the compression."""
    dest = GEN_DIR / "analytics_certin_attack_timeline.mp4"
    f_title = _font(56)
    f_label = _font(40)
    f_big = _font(120)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("DAYS", "BREAK-IN TO DAMAGE, BEFORE", RED, 1.0),
        ("HOURS", "SAME ATTACK, WITH AI AGENTS", NEON, 0.18),
    ]
    finals = [meas.textlength(tag, font=f_big) for tag, _, _, _ in rows]
    base_x, max_len = 990, 760

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "ATTACKS GOT FASTER"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            y0, pitch = 300, 300
            for ri, (tag, label, col, frac) in enumerate(rows):
                rt = t - 0.8 - ri * 0.9
                if rt <= 0:
                    continue
                y = y0 + ri * pitch
                d.text(((W - finals[ri]) / 2, y), tag, font=f_big, fill=col)
                lw = meas.textlength(label, font=f_label)
                d.text(((W - lw) / 2, y + 150), label, font=f_label,
                       fill=GRAY)
                ge = _ease_out_cubic(min(1.0, rt / 1.1))
                ln = int(max_len * frac * ge)
                d.line([(90, y + 235), (90 + ln, y + 235)], fill=col,
                       width=30)
            # footer kicker once bars settle (clip y 1000 < 1090 safe)
            if t > 3.4:
                fk = "CERT-IN: FROM DAYS TO HOURS"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 1000), fk, font=f_label, fill=GRAY)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def kospi_crash(dur=6.0):
    """KOSPI weekly crash 2026-10-16: -14.3% on the week (worst since
    Oct 2008), -8% Thursday, 7 straight losing sessions."""
    dest = GEN_DIR / "analytics_kospi_crash.mp4"
    f_title = _font(56)
    f_label = _font(34)
    f_val = _font(52)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("THIS WEEK", 14.3, "-14.3%"),
        ("THURSDAY", 8.0, "-8%"),
        ("LOSING STREAK", 7.0, "7 DAYS"),
    ]
    maxv = 14.3
    base_x, max_len = 990, 780

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "WORST WEEK SINCE 2008"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            y0, pitch = 250, 190
            for ri, (name, val, tag) in enumerate(rows):
                rt = t - 0.8 - ri * 0.6
                if rt <= 0:
                    continue
                y = y0 + ri * pitch
                nlw = meas.textlength(name, font=f_label)
                d.text((90, y), name, font=f_label, fill=GRAY)
                ge = _ease(min(1.0, rt / 0.9))
                ln = int(max_len * (val / maxv) * ge)
                d.line([(base_x - ln, y + 62), (base_x, y + 62)],
                       fill=RED, width=36)
                ne = _ease_out_cubic(min(1.0, rt / 1.1))
                if "%" in tag:
                    shown = tag if ne >= 1 else "-{:.1f}%".format(val * ne)
                else:
                    shown = tag if ne >= 1 else "{:.0f} DAYS".format(val * ne)
                vw = meas.textlength(shown, font=f_val)
                d.text((base_x - ln - vw - 24, y + 34), shown,
                       font=f_val, fill=NEON)
            # footer kicker once bars settle (clip y 960 < 1090 safe)
            if t > 3.4:
                fk = "KOSPI -14.3% ON THE WEEK"
                flw = meas.textlength(fk, font=f_val)
                d.text(((W - flw) / 2, 960), fk, font=f_val, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def google_links(dur=6.0):
    """Google AI-search link push 2026-10-16: publisher referral traffic
    from Google fell 40% in a year (Chartbeat); AI Overviews now reach
    2B monthly users — so link placement moves serious traffic."""
    dest = GEN_DIR / "analytics_google_links.mp4"
    f_title = _font(56)
    f_label = _font(40)
    f_big = _font(110)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("-40%", 40.0, "-{:.0f}%", "PUBLISHER TRAFFIC FROM GOOGLE, 1 YEAR",
         RED, True),
        ("2B", 2.0, "{:.0f}B", "AI OVERVIEWS MONTHLY USERS", NEON, False),
    ]
    finals = [meas.textlength(tag, font=f_big) for tag, _, _, _, _, _ in rows]
    maxv = 40.0
    base_x, max_len = 990, 780

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "LINKS STRIKE BACK"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_title, fill=NEON)
            y0, pitch = 280, 290
            for ri, (tag, val, fmt, label, col, bar) in enumerate(rows):
                rt = t - 0.8 - ri * 0.9
                if rt <= 0:
                    continue
                y = y0 + ri * pitch
                if bar:
                    # bar grows leftward from the right baseline
                    ge = _ease(min(1.0, rt / 0.9))
                    ln = int(max_len * (val / maxv) * ge)
                    d.line([(base_x - ln, y + 170), (base_x, y + 170)],
                           fill=col, width=34)
                # displayed number: monotonic ease, settles exact
                ne = _ease_out_cubic(min(1.0, rt / 1.1))
                shown = tag if ne >= 1 else fmt.format(val * ne)
                vw = meas.textlength(shown, font=f_big)
                d.text(((W - vw) / 2, y), shown, font=f_big, fill=col)
                lw = meas.textlength(label, font=f_label)
                d.text(((W - lw) / 2, y + 240), label, font=f_label,
                       fill=GRAY)
            # footer kicker once numbers settle (clip y 1000 < 1090 safe)
            if t > 3.6:
                fk = "SMALL TWEAKS, SERIOUS TRAFFIC"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 1000), fk, font=f_label, fill=GRAY)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


# ---------------------------------------------------------------------------
# 2026-10-17 generators (daily run)
# ---------------------------------------------------------------------------

def rogue_hospital_stats(dur=6.0):
    """Rogue agents story, case 1: 24 years of hospital bed data exfiltrated
    after the site blocked the agent. Counter + BLOCKED -> WORKED AROUND."""
    dest = GEN_DIR / "analytics_rogue_hospital.mp4"
    f_mid = _font(48)
    f_label = _font(40)
    f_num = _font(150)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "ROGUE AGENT // CASE 01"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            ne = _ease_out_cubic(min(1.0, t / 1.6))
            shown = str(int(round(24 * ne)))
            tw = meas.textlength(shown, font=f_num)
            d.text(((W - tw) / 2, 300), shown, font=f_num, fill=NEON)
            if t > 0.9:
                lab = "YEARS OF HOSPITAL BED DATA"
                lw = meas.textlength(lab, font=f_label)
                d.text(((W - lw) / 2, 560), lab, font=f_label, fill=GRAY)
            if t > 2.2:
                s2 = "SITE BLOCKED THE REQUEST"
                tw2 = meas.textlength(s2, font=f_mid)
                d.text(((W - tw2) / 2, 700), s2, font=f_mid, fill=GRAY)
            if t > 3.0:
                s3 = "AGENT WORKED AROUND IT"
                tw3 = meas.textlength(s3, font=f_mid)
                d.text(((W - tw3) / 2, 790), s3, font=f_mid, fill=NEON)
            if t > 3.8:
                s4 = "ETHICS CHECK: OVERRIDDEN"
                tw4 = meas.textlength(s4, font=f_label)
                d.text(((W - tw4) / 2, 920), s4, font=f_label, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def rogue_rows_stats(dur=6.0):
    """Rogue agents story, case 2: 147,451 rows pulled from non-public
    tables; changes reverted, access kept, nothing disclosed."""
    dest = GEN_DIR / "analytics_rogue_rows.mp4"
    f_mid = _font(48)
    f_label = _font(40)
    f_num = _font(130)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "ROGUE AGENT // CASE 02"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            ne = _ease_out_cubic(min(1.0, t / 1.8))
            shown = f"{int(round(147451 * ne)):,}"
            tw = meas.textlength(shown, font=f_num)
            d.text(((W - tw) / 2, 300), shown, font=f_num, fill=NEON)
            if t > 1.0:
                lab = "ROWS FROM NON-PUBLIC TABLES"
                lw = meas.textlength(lab, font=f_label)
                d.text(((W - lw) / 2, 520), lab, font=f_label, fill=GRAY)
            if t > 2.4:
                s2 = "CHANGES REVERTED"
                tw2 = meas.textlength(s2, font=f_mid)
                d.text(((W - tw2) / 2, 660), s2, font=f_mid, fill=GRAY)
            if t > 3.1:
                s3 = "ACCESS KEPT"
                tw3 = meas.textlength(s3, font=f_mid)
                d.text(((W - tw3) / 2, 750), s3, font=f_mid, fill=GRAY)
            if t > 3.8:
                s4 = "DISCLOSED: NOTHING"
                tw4 = meas.textlength(s4, font=f_mid)
                d.text(((W - tw4) / 2, 860), s4, font=f_mid, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def argon_harness_gap(dur=6.0):
    """ARC-AGI-3 harness gap: GPT-6 Astra 99.9 vs Argon adapter 97.5 vs
    Argon standard harness 49.8. Same model, same test."""
    dest = GEN_DIR / "analytics_argon_harness.mp4"
    f_mid = _font(48)
    f_label = _font(32)
    f_num = _font(56)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    bars = [
        ("GPT-6 ASTRA", 99.9, "99.9%"),
        ("ARGON ADAPTER", 97.5, "97.5%"),
        ("ARGON STD", 49.8, "49.8%"),
    ]
    maxv = 100

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "ARC-AGI-3 // SAME MODEL, SAME TEST"
            k = int(min(len(title), t / 0.9 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            bw, gap, base_y = 250, 90, 880
            x0 = (W - (3 * bw + 2 * gap)) // 2
            for j, (label, val, tag) in enumerate(bars):
                bt = max(0.0, (t - 0.9 - j * 0.5) / 1.2)
                be = _ease(bt)
                bh = int(560 * (val / maxv) * be)
                x = x0 + j * (bw + gap)
                col = RED if j == 2 else (NEON if j == 0 else DIM)
                if bh > 0:
                    d.rectangle([x, base_y - bh, x + bw, base_y], fill=col)
                if bt > 0.15:
                    ne = _ease_out_cubic(min(1.0, bt / 1.1))
                    shown = f"{val * ne:.1f}%"
                    if ne >= 1:
                        shown = tag
                    tw2 = meas.textlength(shown, font=f_num)
                    d.text((x + (bw - tw2) / 2, base_y - bh - 80), shown,
                           font=f_num, fill=col)
                    lw = meas.textlength(label, font=f_label)
                    d.text((x + (bw - lw) / 2, base_y + 24), label,
                           font=f_label, fill=GRAY)
            if t > 3.8:
                fk = "THE HARNESS DOES HALF THE WORK"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 990), fk, font=f_label, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def mai_base2_specs(dur=6.0):
    """MAI-Base-2 terminal stats card: 2.8T total, 80B active, 16k GB200,
    38 days, 50T tokens. Kicker: efficiency claim is Microsoft's own."""
    dest = GEN_DIR / "analytics_mai_base2.mp4"
    f_mid = _font(48)
    f_label = _font(40)
    f_num = _font(64)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    rows = [
        ("2.8T", "TOTAL PARAMETERS"),
        ("80B", "ACTIVE PER TOKEN"),
        ("16,000", "NVIDIA GB200 GPUS"),
        ("38 DAYS", "OF TRAINING"),
        ("50T", "TRAINING TOKENS"),
    ]

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "MAI-BASE-2 // SCALE"
            k = int(min(len(title), t / 0.7 * len(title)))
            d.text((80, 70), title[:k], font=f_mid, fill=NEON)
            y0, pitch = 210, 138
            for j, (num, lab) in enumerate(rows):
                rt = max(0.0, (t - 0.7 - j * 0.45) / 0.5)
                if rt <= 0:
                    continue
                y = y0 + j * pitch
                d.text((80, y), num, font=f_num, fill=NEON)
                nw = meas.textlength(num, font=f_num)
                d.text((80 + nw + 30, y + 14), lab, font=f_label,
                       fill=GRAY)
            if t > 3.6:
                fk = "4-12x THE EFFICIENCY (THEIR MATH)"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 960), fk, font=f_label, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest




def deepseek_deepswe_bars(dur=6.0):
    """DeepSWE v1.1 coding benchmark: DeepSeek V4.1-Flash 77.0 vs
    Claude Opus 5 74.0 vs GPT-5.6 Sol 73.0 (DeepSeek's own scoreboard)."""
    dest = GEN_DIR / "analytics_deepseek_deepswe.mp4"
    f_mid = _font(48)
    f_label = _font(30)
    f_num = _font(56)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    bars = [
        ("DEEPSEEK V4.1-FLASH", 77.0, "77.0"),
        ("CLAUDE OPUS 5", 74.0, "74.0"),
        ("GPT-5.6 SOL", 73.0, "73.0"),
    ]
    maxv = 85

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "DEEPSWE V1.1 // CODING BENCHMARK"
            k = int(min(len(title), t / 0.9 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            bw, gap, base_y = 250, 90, 880
            x0 = (W - (3 * bw + 2 * gap)) // 2
            for j, (label, val, tag) in enumerate(bars):
                bt = max(0.0, (t - 0.9 - j * 0.5) / 1.2)
                be = _ease(bt)
                bh = int(560 * (val / maxv) * be)
                x = x0 + j * (bw + gap)
                col = NEON if j == 0 else DIM
                if bh > 0:
                    d.rectangle([x, base_y - bh, x + bw, base_y], fill=col)
                if bt > 0.15:
                    ne = _ease_out_cubic(min(1.0, bt / 1.1))
                    shown = f"{val * ne:.1f}"
                    if ne >= 1:
                        shown = tag
                    tw2 = meas.textlength(shown, font=f_num)
                    d.text((x + (bw - tw2) / 2, base_y - bh - 80), shown,
                           font=f_num, fill=col)
                    lw = meas.textlength(label, font=f_label)
                    d.text((x + (bw - lw) / 2, base_y + 24), label,
                           font=f_label, fill=GRAY)
            if t > 3.8:
                fk = "DEEPSEEK'S OWN SCOREBOARD"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 990), fk, font=f_label, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def rtx_spark_memory(dur=6.0):
    """RTX Spark unified memory: 24GB base vs 128GB max config."""
    dest = GEN_DIR / "analytics_rtx_spark_memory.mp4"
    f_mid = _font(48)
    f_label = _font(32)
    f_num = _font(56)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))
    bars = [
        ("BASE CONFIG", 24, "24 GB"),
        ("MAX CONFIG", 128, "128 GB"),
    ]
    maxv = 140

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "UNIFIED MEMORY // LOCAL AI"
            k = int(min(len(title), t / 0.9 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            bw, gap, base_y = 300, 120, 880
            x0 = (W - (2 * bw + gap)) // 2
            for j, (label, val, tag) in enumerate(bars):
                bt = max(0.0, (t - 0.9 - j * 0.5) / 1.2)
                be = _ease(bt)
                bh = int(560 * (val / maxv) * be)
                x = x0 + j * (bw + gap)
                col = NEON if j == 1 else DIM
                if bh > 0:
                    d.rectangle([x, base_y - bh, x + bw, base_y], fill=col)
                if bt > 0.15:
                    ne = _ease_out_cubic(min(1.0, bt / 1.1))
                    shown = f"{val * ne:.0f} GB"
                    if ne >= 1:
                        shown = tag
                    tw2 = meas.textlength(shown, font=f_num)
                    d.text((x + (bw - tw2) / 2, base_y - bh - 80), shown,
                           font=f_num, fill=col)
                    lw = meas.textlength(label, font=f_label)
                    d.text((x + (bw - lw) / 2, base_y + 24), label,
                           font=f_label, fill=GRAY)
            if t > 3.8:
                fk = "5.3X THE MEMORY FOR LOCAL MODELS"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 990), fk, font=f_label, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest




def deepseek_api_price(dur=6.0):
    """DeepSeek Search + Fetch APIs: $0.75 per 1,000 calls, open to all."""
    dest = GEN_DIR / "analytics_deepseek_api_price.mp4"
    f_mid = _font(48)
    f_label = _font(32)
    f_big = _font(64)
    meas = ImageDraw.Draw(Image.new("RGB", (W, H)))

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "SEARCH + FETCH API // PRICING"
            k = int(min(len(title), t / 0.9 * len(title)))
            d.text((80, 80), title[:k], font=f_mid, fill=NEON)
            rows = [
                ("SEARCH API", "$0.75 / 1K CALLS"),
                ("FETCH API", "$0.75 / 1K CALLS"),
            ]
            y0, pitch = 300, 220
            for j, (lab, val) in enumerate(rows):
                rt = max(0.0, (t - 0.9 - j * 0.5) / 0.6)
                if rt <= 0:
                    continue
                y = y0 + j * pitch
                d.text((80, y), lab, font=f_label, fill=GRAY)
                ne = _ease_out_cubic(min(1.0, rt / 1.0))
                vx = 80 + ne * 40
                d.text((vx, y + 50), val, font=f_big, fill=NEON)
            if t > 3.2:
                fk = "OPEN TO ALL DEVELOPERS"
                flw = meas.textlength(fk, font=f_label)
                d.text(((W - flw) / 2, 860), fk, font=f_label, fill=NEON)
            if t > 4.0:
                fk2 = "FREE VIA HARNESS UNTIL NOV 1"
                f2w = meas.textlength(fk2, font=f_label)
                d.text(((W - f2w) / 2, 940), fk2, font=f_label, fill=DIM)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest




def spacex_giveaway_math(dur=6.0):
    """Musk's SpaceX share pledge: 73M kids x $146 = ~$10.7B. Counters."""
    dest = GEN_DIR / "analytics_spacex_giveaway_math.mp4"
    f_title = _font(56)
    f_label = _font(42)
    f_num = _font(64)
    f_big = _font(110)

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "DOING THE MATH"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 60), title[:k], font=f_title, fill=NEON)
            # kids counter
            if t > 0.7:
                p = _ease_out_cubic(min(1.0, (t - 0.7) / 1.4))
                d.text((80, 230), "KIDS UNDER 18", font=f_label, fill=GRAY)
                d.text((80, 290), f"{int(73000000 * p):,}", font=f_num, fill=NEON)
            # price
            if t > 1.6:
                p = _ease_out_cubic(min(1.0, (t - 1.6) / 1.2))
                d.text((80, 450), "PRICE PER SHARE", font=f_label, fill=GRAY)
                d.text((80, 510), f"${int(146 * p)}", font=f_num, fill=NEON)
            # total
            if t > 2.8:
                p = _ease_out_cubic(min(1.0, (t - 2.8) / 1.8))
                d.text((80, 700), "THE GIVEAWAY", font=f_label, fill=GRAY)
                d.text((80, 770), f"${10.7 * p:.1f}B", font=f_big, fill=NEON)
            if t > 4.6:
                d.text((80, 950), "DELIVERY PLAN: NONE YET", font=f_label, fill=RED)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def hacker_agent_numbers(dur=6.0):
    """Hacker AI-agent breach stats: 1200 probed, 23h each, 100+ hit, $5k."""
    dest = GEN_DIR / "analytics_hacker_agent_numbers.mp4"
    f_title = _font(56)
    f_label = _font(40)
    f_num = _font(60)
    f_big = _font(96)
    rows = [
        ("SITES PROBED", 1200, "{:,}"),
        ("HOURS PER BREACH", 23, "{:,}"),
        ("SITES BREACHED", 100, "{}+"),
        ("TOKEN COST", 5000, "${:,}"),
    ]

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "ONE HACKER, AI AGENTS"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 60), title[:k], font=f_title, fill=NEON)
            y0 = 210
            for ri, (label, val, fmt) in enumerate(rows):
                rt = t - 0.7 - ri * 0.6
                if rt <= 0:
                    continue
                p = _ease_out_cubic(min(1.0, rt / 1.0))
                y = y0 + ri * 150
                d.text((80, y), label, font=f_label, fill=GRAY)
                txt = fmt.format(int(val * p))
                d.text((80, y + 52), txt, font=f_num, fill=NEON)
            if t > 3.4:
                p = _ease_out_cubic(min(1.0, (t - 3.4) / 1.0))
                d.text((80, 840), "COST PER BREACH", font=f_label, fill=GRAY)
                d.text((80, 900), f"${int(50 * p)}", font=f_big, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def nscale_ninety_billion(dur=6.0):
    """Anthropic x Nscale: $45B + $45B = $90B. Animated bars + total."""
    dest = GEN_DIR / "analytics_nscale_ninety_billion.mp4"
    f_title = _font(56)
    f_label = _font(42)
    f_num = _font(56)
    f_big = _font(110)
    bars = [("AUG DEAL", 45), ("NEW DEAL", 45)]

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "ANTHROPIC'S COMPUTE BILL"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 60), title[:k], font=f_title, fill=NEON)
            y0 = 240
            for bi, (name, val) in enumerate(bars):
                bt = t - 0.7 - bi * 0.8
                if bt <= 0:
                    continue
                d.text((80, y0 + bi * 200), name, font=f_label, fill=GRAY)
                bw = int(700 * _ease(bt / 0.9))
                d.rectangle([80, y0 + bi * 200 + 62, 780, y0 + bi * 200 + 108],
                            fill=(8, 24, 8))
                if bw > 0:
                    d.rectangle([80, y0 + bi * 200 + 62, 80 + bw,
                                 y0 + bi * 200 + 108], fill=NEON)
                ne = _ease_out_cubic(min(1.0, bt / 0.9))
                d.text((810, y0 + bi * 200 + 52), f"${int(val * ne)}B",
                       font=f_num, fill=NEON)
            if t > 2.8:
                p = _ease_out_cubic(min(1.0, (t - 2.8) / 1.6))
                d.text((80, 720), "COMBINED", font=f_label, fill=GRAY)
                d.text((80, 790), f"${int(90 * p)}B", font=f_big, fill=NEON)
            if t > 4.6:
                d.text((80, 960), "ONE CAMPUS, WEST VIRGINIA", font=f_label,
                       fill=GRAY)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest


def aegis_thresholds(dur=6.0):
    """AEGIS Act pause thresholds: 50+ deaths/serious injuries or $1B damage."""
    dest = GEN_DIR / "analytics_aegis_thresholds.mp4"
    f_title = _font(56)
    f_label = _font(42)
    f_num = _font(72)
    f_big = _font(100)

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "PAUSE ONLY IF"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 60), title[:k], font=f_title, fill=NEON)
            if t > 0.7:
                p = _ease_out_cubic(min(1.0, (t - 0.7) / 1.2))
                d.text((80, 230), "DEATHS OR SERIOUS INJURY", font=f_label,
                       fill=GRAY)
                d.text((80, 300), f"{int(50 * p)}+", font=f_big, fill=RED)
            if t > 1.9:
                p = _ease_out_cubic(min(1.0, (t - 1.9) / 1.2))
                d.text((80, 500), "OR DAMAGE", font=f_label, fill=GRAY)
                d.text((80, 570), f"${p:.1f}B", font=f_big, fill=RED)
            if t > 3.2:
                d.text((80, 780), "FROM A SINGLE INCIDENT", font=f_label,
                       fill=GRAY)
            if t > 4.0:
                d.text((80, 900), "COMMERCE ASKS, COURT ORDERS", font=f_label,
                       fill=NEON)
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
    muse_wonder_benchmark()
    maia_300_specs()
    ai_oversight_letter()
    asia_selloff()
    imf_warning()
    asml_record_quarter()
    rogue_hospital_stats()
    rogue_rows_stats()
    argon_harness_gap()
    mai_base2_specs()
    deepseek_deepswe_bars()
    rtx_spark_memory()
    deepseek_api_price()
    spacex_giveaway_math()
    hacker_agent_numbers()
    nscale_ninety_billion()
    aegis_thresholds()


def ai_token_surge(dur=6.0):
    """Animated rising bars: AI-token 24h surge after Musk's Tesla-AGI post.
    TAO +7.4%, VIRTUALS +7.4%, KITE +6.6%, ICP +6.4%, FET +4.7%.
    Displayed numbers count up monotonically — never overshoot."""
    dest = GEN_DIR / "analytics_ai_token_surge.mp4"
    f_title = _font(56)
    f_label = _font(44)
    f_num = _font(52)
    bars = [
        ("TAO", 7.4, "+7.4%"),
        ("VIRTUALS", 7.4, "+7.4%"),
        ("KITE", 6.6, "+6.6%"),
        ("ICP", 6.4, "+6.4%"),
        ("FET", 4.7, "+4.7%"),
    ]
    maxv = 7.4

    def frames(n):
        for i in range(n):
            t = i / FPS
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            title = "AI TOKENS SURGE"
            k = int(min(len(title), t / 0.8 * len(title)))
            d.text((80, 60), title[:k], font=f_title, fill=NEON)
            sub = "24H AFTER MUSK'S POST"
            if t > 0.5:
                d.text((80, 140), sub, font=f_label, fill=GRAY)
            y0 = 250
            for bi, (name, val, txt) in enumerate(bars):
                bt = t - 0.8 - bi * 0.55
                if bt <= 0:
                    continue
                p = _ease(bt / 0.7)
                bw = int(700 * (val / maxv) * p)
                y = y0 + bi * 160
                d.text((80, y), name, font=f_label, fill=GRAY)
                d.rectangle([80, y + 62, 780, y + 108], fill=(8, 24, 8))
                if bw > 0:
                    d.rectangle([80, y + 62, 80 + bw, y + 108], fill=NEON)
                if p > 0.1:
                    ne = _ease_out_cubic(min(1.0, bt / 0.7))
                    shown = txt if ne >= 1 else f"+{val * ne:.1f}%"
                    d.text((810, y + 52), shown, font=f_num, fill=NEON)
            yield img

    _write(frames, int(dur * FPS), dest)
    return dest
