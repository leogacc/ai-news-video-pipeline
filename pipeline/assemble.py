#!/usr/bin/env python3
"""Declarative Clip Assembler (pipeline/assemble.py, v2026.11.06.5).

Integrates multi-shot visuals (moving video, Remotion motion graphics,
vision-cropped stills, and official tweet cards) with Dynamic Hug geometry,
offline Kokoro TTS narration, and glowing terminal typewriter captions
into broadcast-grade 1080x1920 30fps H.264 vertical video clips.

Complies strictly with channel standards:
- Pure black canvas (#000000)
- Neon green terminal captions (#39FF14) top-anchored at y=1513 below bio
- Dynamic Hug geometry: Title above content, single regular Source bio below,
  watermark @leos.logos at alpha 51 beneath bio
- Audio normalized to -14 LUFS (EBU R128)
- H.264 High L4.0 with faststart for instant streaming
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import animations
import captions
import clip_frames
import google_tts
import qa
import tts
import tweet_card
import numpy as np
import soundfile as sf
from assets.generate_sfx import ensure_sfx, SAMPLE_RATE

logging.basicConfig(level=logging.INFO, format="[assemble] %(message)s")
logger = logging.getLogger("assemble")

FFMPEG = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/usr/bin/ffprobe"


def probe_video(video_path: Path | str) -> Dict[str, Any]:
    """Inspect video properties via ffprobe."""
    cmd = [
        FFPROBE,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,codec_name,duration,nb_frames",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    stream = data.get("streams", [{}])[0]
    fmt = data.get("format", {})
    dur = float(stream.get("duration") or fmt.get("duration") or 0.0)
    return {
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "codec": stream.get("codec_name", ""),
        "fps": stream.get("r_frame_rate", "30/1"),
        "duration": dur,
    }


def generate_karaoke_ass(
    words: List[Tuple[float, float, str]],
    output_ass: Path | str,
    font_size: int = 44,
    margin_v: int = 1205,
) -> Path:
    """Generate top-anchored Terminal Console .ass captions inside the frosted window.

    Pacing & Styling (Phase 9):
    - True per-character teletype typing effect (letters reveal as spoken).
    - 3-line terminal console capacity: phrases accumulate up to 3 lines before clearing.
    - Electric Cyber Yellow (#FFE600 -> &H0000E6FF) active typed character/word.
    - Glowing neon green terminal block cursor (█ -> &H0014FF39) trailing active character.
    - Neon Green (#39FF14 -> &H0014FF39) completed words.
    - Clean text outline mode (BorderStyle=1, Outline=2, Shadow=0) seamlessly integrating
      directly over the frosted dark glass terminal window overlay.
    - Top-anchored safe-zone positioning nested inside terminal client area (MarginV=1205, Alignment=7, MarginL=100).
    - Active prompt (> █) from 0.00s until narration begins.
    """
    green = "&H0014FF39"   # #39FF14
    yellow = "&H0000E6FF"  # #FFE600

    # Load measurement font
    try:
        meas_font = ImageFont.truetype(captions.FONT_PATH, font_size)
    except Exception:
        meas_font = captions._font()

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Terminal,DejaVu Sans Mono,{font_size},{green},{yellow},&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,7,100,100,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    if not words:
        out_p = Path(output_ass).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(header + f"Dialogue: 0,0:00:00.00,0:00:10.00,Terminal,,0,0,0,,> {{\\c{green}&}}█\n", encoding="utf-8")
        return out_p

    # Measurement helpers for 3-line wrapping (max client width ~880px)
    meas = ImageDraw.Draw(Image.new("RGB", (1080, 1920)))
    space_w = meas.textlength(" ", font=meas_font)
    prompt_w = meas.textlength("> ", font=meas_font)
    indent_w = meas.textlength("  ", font=meas_font)
    max_client_w = 880

    def wrap_words(item_list):
        lines = []
        cur_line = []
        cur_w = 0
        for idx, (_, _, wd) in enumerate(item_list):
            wd_w = meas.textlength(wd.upper(), font=meas_font)
            pfx_w = prompt_w if not lines else indent_w
            add_w = wd_w if not cur_line else space_w + wd_w
            if cur_w + add_w + (pfx_w if not cur_line else 0) <= max_client_w:
                cur_line.append(idx)
                cur_w += add_w
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = [idx]
                cur_w = wd_w + indent_w
        if cur_line:
            lines.append(cur_line)
        return lines

    # Group into phrases that fit up to 3 lines or break on natural sentence ends (.?!)
    phrases: List[List[Tuple[float, float, str]]] = []
    cur: List[Tuple[float, float, str]] = []
    for s, e, w in words:
        trial = cur + [(s, e, w)]
        wrapped = wrap_words(trial)
        sentence_end = bool(re.search(r"[.?!]$", w))

        if len(wrapped) > 3:
            if cur:
                phrases.append(cur)
            cur = [(s, e, w)]
        elif sentence_end or (cur and e - cur[0][0] >= 4.2):
            phrases.append(trial)
            cur = []
        else:
            cur = trial
    if cur:
        phrases.append(cur)

    events = []

    # Initial idle prompt before narration begins (0.00s to words[0][0])
    first_start = words[0][0]
    if first_start > 0.05:
        events.append(
            f"Dialogue: 0,0:00:00.00,{captions.ts(first_start)},Terminal,,0,0,0,,> {{\\c{green}&}}█"
        )

    for pi, ph in enumerate(phrases):
        lines = wrap_words(ph)

        for wi, (sw, ew, raw_w) in enumerate(ph):
            w_text = raw_w.upper().replace("{", r"\{").replace("}", r"\}")
            n_chars = max(1, len(w_text))
            w_dur = max(0.04, ew - sw)
            char_dur = w_dur / n_chars

            next_start = ph[wi + 1][0] if wi < len(ph) - 1 else ew

            for ci in range(n_chars):
                c_start = sw + ci * char_dur
                if ci < n_chars - 1:
                    c_end = sw + (ci + 1) * char_dur
                else:
                    c_end = max(c_start + 0.03, next_start if wi < len(ph) - 1 else min(ew + 0.35, ew + 0.35))
                c_end = max(c_end, c_start + 0.03)

                # Build up to 3 lines
                line_strs = []
                for li, line_indices in enumerate(lines):
                    if line_indices[0] > wi:
                        continue
                    visible_indices = [idx for idx in line_indices if idx <= wi]
                    words_in_line = []
                    for idx in visible_indices:
                        idx_w = ph[idx][2].upper().replace("{", r"\{").replace("}", r"\}")
                        if idx < wi:
                            words_in_line.append(r"{\c" + green + r"&}" + idx_w)
                        elif idx == wi:
                            typed_part = idx_w[: ci + 1]
                            words_in_line.append(r"{\c" + yellow + r"&}" + typed_part + r"{\c" + green + r"&}█")
                    prefix = "> " if li == 0 else "  "
                    line_strs.append(prefix + " ".join(words_in_line))

                ev_text = r"\N".join(line_strs)
                events.append(
                    f"Dialogue: 0,{captions.ts(c_start)},{captions.ts(c_end)},Terminal,,0,0,0,,{ev_text}"
                )

            # If there is a perceptible silence gap before next word, hold completed word in green with resting cursor
            if wi < len(ph) - 1:
                next_w_start = ph[wi + 1][0]
                if next_w_start > ew + 0.06:
                    line_strs = []
                    for li, line_indices in enumerate(lines):
                        if line_indices[0] > wi:
                            continue
                        visible_indices = [idx for idx in line_indices if idx <= wi]
                        words_in_line = [r"{\c" + green + r"&}" + ph[idx][2].upper().replace("{", r"\{").replace("}", r"\}") for idx in visible_indices]
                        if wi in visible_indices:
                            words_in_line[-1] += r" {\c" + green + r"&}█"
                        prefix = "> " if li == 0 else "  "
                        line_strs.append(prefix + " ".join(words_in_line))
                    ev_gap = r"\N".join(line_strs)
                    events.append(
                        f"Dialogue: 0,{captions.ts(ew)},{captions.ts(next_w_start)},Terminal,,0,0,0,,{ev_gap}"
                    )

        # Gap between phrases: hold the completed phrase with cursor until next phrase starts
        if pi < len(phrases) - 1:
            next_ph_start = phrases[pi + 1][0][0]
            phrase_end_sec = ph[-1][1]
            if next_ph_start > phrase_end_sec + 0.08:
                hold_start = phrase_end_sec
                hold_end = next_ph_start
                hold_strs = []
                for li, line_indices in enumerate(lines):
                    line_words = [r"{\c" + green + r"&}" + ph[idx][2].upper().replace("{", r"\{").replace("}", r"\}") for idx in line_indices]
                    if li == len(lines) - 1:
                        line_words[-1] += r" {\c" + green + r"&}█"
                    prefix = "> " if li == 0 else "  "
                    hold_strs.append(prefix + " ".join(line_words))
                ev_hold = r"\N".join(hold_strs)
                events.append(
                    f"Dialogue: 0,{captions.ts(hold_start)},{captions.ts(hold_end)},Terminal,,0,0,0,,{ev_hold}"
                )

    ass_content = header + "\n".join(events) + "\n"
    out_p = Path(output_ass).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(ass_content, encoding="utf-8")
    return out_p


def generate_sfx_track(
    durations: List[float],
    shots_spec: List[Dict[str, Any]],
    total_dur: float,
    output_path: Path,
) -> Path:
    """Generates a sample-accurate 48kHz stereo sfx.wav stream for cuts and milestones."""
    sfx_files = ensure_sfx()
    whoosh, _ = sf.read(str(sfx_files["whoosh"]))
    click, _ = sf.read(str(sfx_files["click"]))
    bass, _ = sf.read(str(sfx_files["bass"]))

    total_samples = int(math.ceil(total_dur * SAMPLE_RATE))
    sfx_track = np.zeros((total_samples, 2), dtype=np.float32)

    def mix_in(audio_clip: np.ndarray, t_sec: float):
        start_samp = int(round(t_sec * SAMPLE_RATE))
        if start_samp < 0:
            audio_clip = audio_clip[-start_samp:]
            start_samp = 0
        end_samp = start_samp + len(audio_clip)
        if start_samp >= total_samples:
            return
        if end_samp > total_samples:
            audio_clip = audio_clip[: total_samples - start_samp]
            end_samp = total_samples
        sfx_track[start_samp:end_samp] += audio_clip

    t_cursor = 0.0
    for i, dur in enumerate(durations):
        # Whoosh accent slightly before cut boundary (for every transition after shot 0)
        if i > 0:
            mix_in(whoosh, t_cursor - 0.10)

        # Milestone sound effects for animated graphics and tweet cards
        shot = shots_spec[i] if i < len(shots_spec) else {}
        shot_type = shot.get("type", "")
        if shot_type in ("remotion", "tweet_card"):
            # Deep sub-bass drop on hero entry
            mix_in(bass, t_cursor + 0.10)
            # Snappy tactile tick on takeaway highlight or metric reveal at 1.2s
            if dur >= 1.5:
                mix_in(click, t_cursor + 1.20)

        t_cursor += dur

    # Prevent digital clipping
    peak = np.max(np.abs(sfx_track))
    if peak > 0.95:
        sfx_track = sfx_track * (0.95 / peak)

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), sfx_track, SAMPLE_RATE, subtype="PCM_16")
    logger.info("Synchronized SFX track built -> %s (%.2fs)", output_path, total_dur)
    return output_path


class ClipAssembler:
    """Orchestrates clip assembly from multi-modal shots and narration."""

    def __init__(self, spec: Dict[str, Any], work_dir: Optional[Path] = None):
        self.spec = spec
        self.work_dir = Path(work_dir or tempfile.mkdtemp(prefix="assemble_"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

        raw_title = spec.get("title_lines") or spec.get("title") or ["AI BREAKTHROUGH"]
        self.title_lines = [raw_title] if isinstance(raw_title, str) else list(raw_title)

        raw_bio = spec.get("bio_lines") or spec.get("bio") or ["Source: Verified Research, 2026"]
        self.bio_lines = [raw_bio] if isinstance(raw_bio, str) else list(raw_bio)

        raw_script = spec.get("script") or spec.get("narration") or []
        if isinstance(raw_script, str):
            self.script_sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', raw_script) if s.strip()]
        else:
            self.script_sentences = list(raw_script)

        self.shots_spec: List[Dict[str, Any]] = spec.get("shots", [])

        music_cfg = spec.get("music")
        if music_cfg is True:
            default_music = ROOT / "assets" / "music" / "ai_digest_bed.mp3"
            self.music_path = default_music if default_music.is_file() else None
        elif isinstance(music_cfg, (str, Path)) and music_cfg:
            self.music_path = Path(music_cfg).resolve()
        else:
            self.music_path = None

        self.enable_sfx = spec.get("enable_sfx", True)

    def synthesize_narration(self) -> Tuple[Path, List[Tuple[float, float, str]], float]:
        """Synthesize script text via Google Cloud Studio-O or Kokoro TTS fallback."""
        full_text = " ".join(self.script_sentences)
        voice_cfg = self.spec.get("voice") or google_tts.DEFAULT_VOICE
        speed_cfg = float(self.spec.get("speaking_rate") or google_tts.DEFAULT_SPEAKING_RATE)

        wav, words, dur, engine = google_tts.synthesize_speech(
            full_text,
            voice_name=voice_cfg,
            speaking_rate=speed_cfg,
            allow_fallback=True,
        )

        sr = 24000
        wav_path = self.work_dir / "narration.wav"
        import soundfile as sf
        sf.write(str(wav_path), wav, sr)

        logger.info("Narration synthesized via %s: %.2fs (%d words)", engine, dur, len(words))

        # Format words for caption generation: [(start, end, word)]
        word_items = [(w[1], w[2], w[0]) for w in words]
        words_json_path = self.work_dir / "words.json"
        with open(words_json_path, "w") as f:
            json.dump([{"start": s, "end": e, "word": w} for s, e, w in word_items], f, indent=2)

        return wav_path, word_items, dur

    def resolve_shot_durations(self, total_audio_dur: float) -> List[float]:
        """Allocate durations for each shot based on 'auto' or explicit numbers.

        Defensively scales down explicit shot durations when explicit_sum + 1.5 * n_auto > target_total,
        and mathematically guarantees sum(durations) == target_total (or abs(sum(durations) - total_audio_dur) <= 0.35s).
        """
        n_shots = len(self.shots_spec)
        if n_shots == 0:
            raise ValueError("No shots defined in spec")

        # Provide a comfortable 0.3s visual hold at the end of the clip
        target_total = round(total_audio_dur + 0.3, 2)

        durations: List[float] = []
        auto_indices = []

        for i, s in enumerate(self.shots_spec):
            dur = s.get("duration")
            if dur is None or dur == "auto":
                auto_indices.append(i)
                durations.append(0.0)
            else:
                durations.append(float(dur))

        explicit_sum = sum(durations)
        n_auto = len(auto_indices)

        if n_auto > 0:
            min_auto_needed = 1.5 * n_auto
            if explicit_sum + min_auto_needed <= target_total:
                # Standard case: plenty of headroom for auto shots
                remaining = target_total - explicit_sum
                per_auto = remaining / n_auto
                for idx in auto_indices:
                    durations[idx] = round(per_auto, 2)
            else:
                # Defensive scale down: explicit durations + auto minimum exceed target_total
                if target_total > min_auto_needed and explicit_sum > 0:
                    avail_for_explicit = target_total - min_auto_needed
                    scale = avail_for_explicit / explicit_sum
                    for i in range(n_shots):
                        if i not in auto_indices:
                            durations[i] = round(durations[i] * scale, 2)
                    for idx in auto_indices:
                        durations[idx] = 1.5
                else:
                    # Ultra-short total: scale all shots proportionally
                    nominal_total = explicit_sum + min_auto_needed
                    if nominal_total > 0:
                        scale = target_total / nominal_total
                        for i in range(n_shots):
                            if i in auto_indices:
                                durations[i] = round(1.5 * scale, 2)
                            else:
                                durations[i] = round(durations[i] * scale, 2)
                    else:
                        per_shot = target_total / n_shots
                        durations = [round(per_shot, 2) for _ in range(n_shots)]
        else:
            # No auto shots: adjust explicit durations to match target_total exactly
            if explicit_sum < target_total:
                durations[-1] += round(target_total - explicit_sum, 2)
            elif explicit_sum > target_total:
                diff = explicit_sum - target_total
                if durations[-1] - diff >= 1.5:
                    durations[-1] = round(durations[-1] - diff, 2)
                else:
                    scale = target_total / explicit_sum
                    durations = [round(d * scale, 2) for d in durations]

        # Exact mathematical guarantee: eliminate centisecond rounding drift
        current_sum = round(sum(durations), 2)
        drift = round(target_total - current_sum, 2)
        if abs(drift) > 0.0001:
            adj_idx = auto_indices[-1] if n_auto > 0 else (n_shots - 1)
            durations[adj_idx] = round(durations[adj_idx] + drift, 2)

        logger.info("Resolved shot durations: %s (Total: %.2fs)", durations, sum(durations))
        return durations

    def render_shot(self, shot_idx: int, shot: Dict[str, Any], duration: float) -> Path:
        """Render a single shot into a standardized 1080x1920 30fps H.264 MP4."""
        shot_type = shot.get("type", "still")
        out_shot = self.work_dir / f"shot_{shot_idx:02d}.mp4"
        logger.info("Rendering shot %d (%s, %.2fs)...", shot_idx, shot_type, duration)

        if shot_type == "animation":
            src_file = shot.get("src") or shot.get("path")
            if src_file and Path(src_file).is_file():
                meta = probe_video(src_file)
                src_dur = meta.get("duration", 0)
                if abs(src_dur - duration) <= 0.1:
                    shutil.copyfile(src_file, out_shot)
                    return out_shot
                else:
                    cmd = [
                        FFMPEG,
                        "-y",
                        "-stream_loop",
                        "-1",
                        "-i",
                        str(src_file),
                        "-t",
                        f"{duration:.3f}",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "18",
                        "-pix_fmt",
                        "yuv420p",
                        "-r",
                        "30",
                        str(out_shot),
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    return out_shot

            # Remotion motion graphic cutaway
            comp_name = shot.get("composition", "BenchmarkLadder")
            comp_props = shot.get("props", {})
            # If title / source are not provided in props, default to clip spec
            if "title" not in comp_props and self.title_lines:
                comp_props["title"] = " ".join(self.title_lines)
            if "source" not in comp_props and self.bio_lines:
                comp_props["source"] = self.bio_lines[0]

            frames = int(math.ceil(duration * 30))
            animations.render_animation(
                composition=comp_name,
                props=comp_props,
                output_path=out_shot,
                duration_frames=frames,
                fps=30,
            )
            return out_shot

        elif shot_type == "tweet_card":
            # Official tweet card via tweet_card.py + Remotion TweetCard3D (with 2D Ken Burns fallback)
            src_url = shot.get("src") or shot.get("path") or ""
            raw_png = self.work_dir / f"raw_tweet_{shot_idx}.png"
            if src_url.startswith("http"):
                tweet_card.render_tweet_card(src_url, str(raw_png))
            else:
                raw_png = Path(src_url)

            # Auto-promote to Remotion TweetCard3D
            use_3d = shot.get("use_3d", True)
            if use_3d:
                try:
                    logger.info("Auto-promoting tweet card shot %d to Remotion TweetCard3D...", shot_idx)
                    duration_frames = int(math.ceil(duration * 30))
                    highlight_words = shot.get("highlight_words") or shot.get("highlightWords")
                    title = shot.get("title") or (" ".join(self.title_lines) if self.title_lines else None)
                    subtitle = shot.get("subtitle") or (self.bio_lines[0] if self.bio_lines else None)
                    animations.render_tweet_card_3d(
                        card_image_path=raw_png,
                        output_path=out_shot,
                        title=title,
                        subtitle=subtitle,
                        badge=shot.get("badge", "OFFICIAL X DISPATCH"),
                        source=shot.get("source", "Source: Official X Post / Community Release"),
                        highlight_words=highlight_words,
                        duration_frames=duration_frames,
                    )
                    return out_shot
                except Exception as e:
                    logger.warning("Remotion TweetCard3D failed; falling back to 2D Ken Burns: %s", e)

            im = Image.open(raw_png).convert("RGB")
            vw, vh = im.size

            overlay_img, layout = clip_frames.build_video_overlay(
                self.title_lines, self.bio_lines, vw, vh, max_w=960
            )
            overlay_png = self.work_dir / f"overlay_{shot_idx}.png"
            overlay_img.save(str(overlay_png))

            nw, nh = layout["nw"], layout["nh"]
            nw -= nw % 2
            nh -= nh % 2
            ct = layout["content_top"]
            total_frames = int(math.ceil(duration * 30))
            step = 0.06 / max(1, total_frames)

            # Continuous subtle Ken Burns push-in (100% -> 106%) on inner visual
            vf = (
                f"[0:v]scale={nw}:{nh}:flags=lanczos,"
                f"zoompan=z='min(zoom+{step:.5f},1.06)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={nw}x{nh}:fps=30,"
                f"pad=1080:1920:(1080-{nw})/2:{ct}:color=black[base];"
                f"[base][1:v]overlay=0:0[outv]"
            )

            cmd = [
                FFMPEG,
                "-y",
                "-loop",
                "1",
                "-i",
                str(raw_png),
                "-loop",
                "1",
                "-i",
                str(overlay_png),
                "-t",
                f"{duration:.3f}",
                "-filter_complex",
                vf,
                "-map",
                "[outv]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-level",
                "4.0",
                "-r",
                "30",
                str(out_shot),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return out_shot

        elif shot_type == "still":
            # Still image with Dynamic Hug framing + Ken Burns subtle push-in
            src_path = Path(shot.get("src") or shot.get("path") or "")
            im = Image.open(src_path).convert("RGB")
            vw, vh = im.size

            overlay_img, layout = clip_frames.build_video_overlay(
                self.title_lines, self.bio_lines, vw, vh, max_w=960
            )
            overlay_png = self.work_dir / f"overlay_{shot_idx}.png"
            overlay_img.save(str(overlay_png))

            nw, nh = layout["nw"], layout["nh"]
            nw -= nw % 2
            nh -= nh % 2
            ct = layout["content_top"]
            total_frames = int(math.ceil(duration * 30))
            step = 0.06 / max(1, total_frames)

            # Alternating Ken Burns motion (even: push-in 1.0->1.06, odd: pull-out 1.06->1.0)
            if shot_idx % 2 == 0:
                zoom_expr = f"min(zoom+{step:.5f},1.06)"
            else:
                zoom_expr = f"max(1.06-on*{step:.5f},1.0)"

            vf = (
                f"[0:v]scale={nw}:{nh}:flags=lanczos,"
                f"zoompan=z='{zoom_expr}':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={nw}x{nh}:fps=30,"
                f"pad=1080:1920:(1080-{nw})/2:{ct}:color=black[base];"
                f"[base][1:v]overlay=0:0[outv]"
            )

            cmd = [
                FFMPEG,
                "-y",
                "-loop",
                "1",
                "-i",
                str(src_path),
                "-loop",
                "1",
                "-i",
                str(overlay_png),
                "-t",
                f"{duration:.3f}",
                "-filter_complex",
                vf,
                "-map",
                "[outv]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-level",
                "4.0",
                "-r",
                "30",
                str(out_shot),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return out_shot

        elif shot_type == "video":
            # Moving source video scaled & wrapped in Dynamic Hug overlay
            src_vid = Path(shot.get("src") or shot.get("path") or "")
            meta = probe_video(src_vid)
            vw, vh = meta["width"], meta["height"]

            # Build transparent Dynamic Hug overlay PNG
            overlay_img, layout = clip_frames.build_video_overlay(
                self.title_lines, self.bio_lines, vw, vh, max_w=960
            )
            overlay_png = self.work_dir / f"overlay_{shot_idx}.png"
            overlay_img.save(str(overlay_png))

            nw, nh = layout["nw"], layout["nh"]
            nw -= nw % 2
            nh -= nh % 2
            ct = layout["content_top"]

            # Filtergraph: scale source, pad centered on pure black, overlay Dynamic Hug text
            vf = (
                f"[0:v]scale={nw}:{nh}:flags=lanczos,"
                f"pad=1080:1920:(1080-{nw})/2:{ct}:color=black[base];"
                f"[base][1:v]overlay=0:0[outv]"
            )

            cmd = [
                FFMPEG,
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(src_vid),
                "-loop",
                "1",
                "-i",
                str(overlay_png),
                "-t",
                f"{duration:.3f}",
                "-filter_complex",
                vf,
                "-map",
                "[outv]",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-level",
                "4.0",
                "-r",
                "30",
                str(out_shot),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return out_shot

        else:
            raise ValueError(f"Unsupported shot type: {shot_type}")

    def assemble(self, output_mp4: Path | str) -> Path:
        """Run complete assembly and produce finalized vertical video."""
        out_final = Path(output_mp4).resolve()
        out_final.parent.mkdir(parents=True, exist_ok=True)

        # 1. Synthesize narration audio
        wav_path, word_items, audio_dur = self.synthesize_narration()

        # 2. Resolve shot durations
        durations = self.resolve_shot_durations(audio_dur)

        # 3. Render visual shots
        rendered_shots: List[Path] = []
        for i, (shot_spec, dur) in enumerate(zip(self.shots_spec, durations)):
            shot_file = self.render_shot(i, shot_spec, dur)
            rendered_shots.append(shot_file)

        # 4. Concatenate visual shots with ffmpeg concat filter
        concat_video = self.work_dir / "concat_video.mp4"
        inputs = []
        filter_inputs = []
        for idx, s in enumerate(rendered_shots):
            inputs.extend(["-i", str(s.resolve())])
            filter_inputs.append(f"[{idx}:v]")

        filter_str = f"{''.join(filter_inputs)}concat=n={len(rendered_shots)}:v=1:a=0[v]"
        cmd_concat = [
            FFMPEG,
            "-y",
            *inputs,
            "-filter_complex",
            filter_str,
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            str(concat_video),
        ]
        subprocess.run(cmd_concat, check=True, capture_output=True)

        # 4b. Overlay terminal console window background onto concatenated video
        concat_with_terminal = concat_video
        try:
            terminal_overlay_img = clip_frames.build_terminal_window_overlay()
            terminal_overlay_png = self.work_dir / "terminal_overlay.png"
            terminal_overlay_img.save(str(terminal_overlay_png))

            # Persistent hook banner (Phase 10.2: Hook Velocity across Shots 0 and 1)
            banner_text = self.spec.get("hook_banner") or self.spec.get("title_prefix") or self.spec.get("title") or ""
            banner_png = None
            if banner_text:
                banner_img = clip_frames.build_persistent_hook_banner(banner_text)
                banner_png = self.work_dir / "hook_banner.png"
                banner_img.save(str(banner_png))

            banner_end_t = min(7.5, sum(durations[:2]) if len(durations) >= 2 else (durations[0] if durations else 4.0))

            term_video = self.work_dir / "concat_with_terminal.mp4"
            if banner_png and banner_png.exists():
                filter_desc = (
                    f"[0:v][1:v]overlay=0:0:shortest=1[base];"
                    f"[base][2:v]overlay=0:0:enable='between(t,0,{banner_end_t:.3f})'[v]"
                )
                cmd_overlay = [
                    FFMPEG,
                    "-y",
                    "-i",
                    str(concat_video),
                    "-loop",
                    "1",
                    "-i",
                    str(terminal_overlay_png),
                    "-loop",
                    "1",
                    "-i",
                    str(banner_png),
                    "-filter_complex",
                    filter_desc,
                    "-map",
                    "[v]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    "30",
                    str(term_video),
                ]
            else:
                cmd_overlay = [
                    FFMPEG,
                    "-y",
                    "-i",
                    str(concat_video),
                    "-loop",
                    "1",
                    "-i",
                    str(terminal_overlay_png),
                    "-filter_complex",
                    "[0:v][1:v]overlay=0:0:shortest=1[v]",
                    "-map",
                    "[v]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-pix_fmt",
                    "yuv420p",
                    "-r",
                    "30",
                    str(term_video),
                ]
            subprocess.run(cmd_overlay, check=True, capture_output=True)
            concat_with_terminal = term_video
            logger.info("Terminal window and persistent hook banner overlays composited -> %s", concat_with_terminal)
        except Exception as e:
            logger.warning("Terminal/banner overlay compositing failed; falling back to raw video: %s", e)
            concat_with_terminal = concat_video

        # 5. Generate terminal typewriter .ass captions
        ass_path = self.work_dir / "captions.ass"
        generate_karaoke_ass(word_items, ass_path)

        # Preserve captions alongside output
        final_ass = out_final.parent / "captions.ass"
        try:
            shutil.copyfile(ass_path, final_ass)
        except Exception:
            final_ass = ass_path

        # 6. Multiplex video, burn captions, mix audio with dynamic sidechain ducking & -14 LUFS loudnorm
        logger.info("Multiplexing final clip with audio and burnt-in terminal captions...")
        # Note: In ffmpeg ass filter, escape colon and backslash in path
        escaped_ass = str(ass_path.resolve()).replace(":", "\\:").replace("'", "\\'")

        total_clip_dur = max(audio_dur, sum(durations)) + 1.0

        # Generate synchronized SFX track
        sfx_path = None
        if self.enable_sfx:
            try:
                sfx_file = self.work_dir / "sfx.wav"
                sfx_path = generate_sfx_track(durations, self.shots_spec, total_clip_dur, sfx_file)
            except Exception as e:
                logger.warning("SFX track generation failed; continuing without SFX: %s", e)
                sfx_path = None

        if self.music_path and self.music_path.is_file():
            logger.info("Enabling background audio bed with sidechain ducking: %s", self.music_path.name)
            if sfx_path and sfx_path.is_file():
                filter_complex = (
                    f"[0:v]ass='{escaped_ass}'[v];"
                    f"[1:a]aformat=channel_layouts=stereo:sample_rates=48000,asplit=2[v_main][v_side];"
                    f"[2:a]aloop=loop=-1:size=2e+09,atrim=0:{total_clip_dur:.2f},aformat=channel_layouts=stereo:sample_rates=48000,volume=-16dB[music];"
                    f"[music][v_side]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[music_ducked];"
                    f"[3:a]aformat=channel_layouts=stereo:sample_rates=48000[sfx];"
                    f"[v_main][sfx][music_ducked]amix=inputs=3:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=11:TP=-1.0[outa]"
                )
                inputs = [
                    "-i", str(concat_with_terminal),
                    "-i", str(wav_path),
                    "-i", str(self.music_path.resolve()),
                    "-i", str(sfx_path),
                ]
            else:
                filter_complex = (
                    f"[0:v]ass='{escaped_ass}'[v];"
                    f"[1:a]aformat=channel_layouts=stereo:sample_rates=48000,asplit=2[v_main][v_side];"
                    f"[2:a]aloop=loop=-1:size=2e+09,atrim=0:{total_clip_dur:.2f},aformat=channel_layouts=stereo:sample_rates=48000,volume=-16dB[music];"
                    f"[music][v_side]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[music_ducked];"
                    f"[v_main][music_ducked]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=11:TP=-1.0[outa]"
                )
                inputs = [
                    "-i", str(concat_with_terminal),
                    "-i", str(wav_path),
                    "-i", str(self.music_path.resolve()),
                ]
        else:
            if sfx_path and sfx_path.is_file():
                filter_complex = (
                    f"[0:v]ass='{escaped_ass}'[v];"
                    f"[1:a]aformat=channel_layouts=stereo:sample_rates=48000[v_main];"
                    f"[2:a]aformat=channel_layouts=stereo:sample_rates=48000[sfx];"
                    f"[v_main][sfx]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=11:TP=-1.0[outa]"
                )
                inputs = [
                    "-i", str(concat_with_terminal),
                    "-i", str(wav_path),
                    "-i", str(sfx_path),
                ]
            else:
                filter_complex = (
                    f"[0:v]ass='{escaped_ass}'[v];"
                    f"[1:a]loudnorm=I=-14:LRA=11:TP=-1.0[outa]"
                )
                inputs = [
                    "-i", str(concat_with_terminal),
                    "-i", str(wav_path),
                ]

        cmd_final = [
            FFMPEG,
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.0",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_final),
        ]
        subprocess.run(cmd_final, check=True, capture_output=True)

        # 7. Extract verification stills (10%, 50%, 90% timestamps)
        stills_dir = out_final.parent / "stills"
        stills_dir.mkdir(parents=True, exist_ok=True)
        meta = probe_video(out_final)
        dur = meta["duration"]
        for p in [0.10, 0.50, 0.90]:
            t_sec = dur * p
            still_p = stills_dir / f"still_{int(p*100)}pct.png"
            cmd_still = [
                FFMPEG,
                "-y",
                "-ss",
                f"{t_sec:.2f}",
                "-i",
                str(out_final),
                "-vframes",
                "1",
                str(still_p),
            ]
            subprocess.run(cmd_still, capture_output=True)

        logger.info("Verification stills saved to %s", stills_dir)

        # 8. Automated QA Verification Gate (Strictly Blocking)
        logger.info("Executing Automated Clip QA Gate...")
        failures = qa.check_clip_file(out_final, ass_path=final_ass, stills_dir=stills_dir, verbose=True)
        version_str = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "unknown"
        qa_report = {
            "clip": str(out_final),
            "pipeline_version": version_str,
            "failures": failures,
            "passed": len(failures) == 0,
        }
        (out_final.parent / "qa.json").write_text(json.dumps(qa_report, indent=2))
        if failures:
            logger.error("Automated Clip QA Gate FAILED: %s", failures)
            raise RuntimeError(f"Automated QA Gate Failed: {failures}")
        logger.info("Automated Clip QA Gate PASSED: all delivery specifications verified.")

        return out_final


def assemble_clip(
    spec: Union[Dict[str, Any], str, Path],
    output_mp4: Union[str, Path],
    work_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Convenience function to assemble a clip from a dictionary or YAML/JSON file."""
    if isinstance(spec, (str, Path)):
        p = Path(spec)
        text = p.read_text(encoding="utf-8")
        data = yaml.safe_load(text) if p.suffix in (".yaml", ".yml") else json.loads(text)
    else:
        data = spec

    assembler = ClipAssembler(data, work_dir=Path(work_dir) if work_dir else None)
    return assembler.assemble(output_mp4)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Assemble vertical AI news clips")
    parser.add_argument("spec_pos", nargs="?", default=None, help="Path to clip spec (YAML or JSON)")
    parser.add_argument("--spec", default=None, help="Path to clip spec (YAML or JSON)")
    parser.add_argument("-o", "--out", default=None, help="Output MP4 path")
    parser.add_argument("--work-dir", help="Optional scratch directory")
    args = parser.parse_args()

    spec_path = args.spec or args.spec_pos
    if not spec_path:
        parser.error("clip spec path is required (positional or --spec)")
    if not args.out:
        parser.error("-o / --out is required")

    out_file = assemble_clip(spec_path, args.out, work_dir=args.work_dir)
    print(f"Assembly Complete -> {out_file}")


if __name__ == "__main__":
    main()
