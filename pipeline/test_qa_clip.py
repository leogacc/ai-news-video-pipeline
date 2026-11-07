#!/usr/bin/env python3
"""Unit tests for the Automated Clip QA Gate (pipeline/qa.py).

Verifies strict blocking enforcement of delivery specifications:
- 1080x1920 geometry, 30fps
- H.264 High L4.0, yuv420p
- Faststart container flag (moov before mdat)
- 48kHz audio duration sync and -14 LUFS loudness
- Top-anchored #39FF14 neon green typewriter captions
- Edge-slice still pin detection integration
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "pipeline"))
import qa


class TestClipQAGate(unittest.TestCase):
    """Test suite for pipeline/qa.py check_clip_file."""

    @classmethod
    def setUpClass(cls):
        cls.work_dir = Path(tempfile.mkdtemp(prefix="test_clip_qa_"))
        cls.ffmpeg = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work_dir, ignore_errors=True)

    def _create_synthetic_clip(
        self,
        out_path: Path,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        duration: float = 3.0,
        with_audio: bool = True,
        sample_rate: int = 48000,
        faststart: bool = True,
    ) -> Path:
        """Create a lightweight synthetic MP4 for QA testing."""
        cmd = [
            self.ffmpeg,
            "-y",
            "-f", "lavfi",
            "-i", f"testsrc=size={width}x{height}:rate={fps}:duration={duration}",
        ]
        if with_audio:
            # 440 Hz sine tone with -14 LUFS volume
            cmd.extend([
                "-f", "lavfi",
                "-i", f"sine=frequency=440:sample_rate={sample_rate}:duration={duration}",
                "-af", "loudnorm=I=-14:LRA=11:TP=-1.0",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", str(sample_rate),
            ])
        cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-profile:v", "high",
            "-level", "4.0",
            "-t", f"{duration:.2f}",
        ])
        if faststart:
            cmd.extend(["-movflags", "+faststart"])
        cmd.append(str(out_path))

        subprocess.run(cmd, check=True, capture_output=True)
        return out_path

    def _create_synthetic_ass(
        self,
        out_path: Path,
        margin_v: int = 1180,
        color: str = "&H0014FF39",
        border_style: int = 3,
    ) -> Path:
        """Create a synthetic .ass caption file."""
        content = f"""[Script Info]
Title: Test Captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans Mono,68,{color},&HFF000000,&H40000000,&H40000000,-1,0,0,0,100,100,0,0,{border_style},14,0,7,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.50,Default,,0,0,0,,Testing QA Captions
"""
        out_path.write_text(content, encoding="utf-8")
        return out_path

    def _create_synthetic_stills(self, stills_dir: Path, sliced: bool = False):
        """Create clean or edge-sliced verification stills."""
        stills_dir.mkdir(parents=True, exist_ok=True)
        for pct in [10, 50, 90]:
            p = stills_dir / f"still_{pct}pct.png"
            img = Image.new("RGB", (1080, 1920), color=(0, 0, 0))
            if sliced:
                # Add white margin with clipped black glyph stems at top edge
                draw = ImageDraw.Draw(img)
                draw.rectangle([0, 0, 1080, 10], fill=(245, 245, 245))
                # Add 8 short dark runs (sliced headline signature)
                for x in range(50, 450, 50):
                    draw.rectangle([x, 0, x + 15, 2], fill=(20, 20, 20))
            img.save(str(p))

    def test_passing_clip_clears_all_checks(self):
        """A properly formatted 1080x1920 30fps clip with audio, captions, and stills passes QA."""
        clip_p = self.work_dir / "passing_clip.mp4"
        self._create_synthetic_clip(clip_p)
        ass_p = self.work_dir / "captions.ass"
        self._create_synthetic_ass(ass_p)
        stills_d = self.work_dir / "stills"
        self._create_synthetic_stills(stills_d, sliced=False)

        failures = qa.check_clip_file(clip_p, ass_path=ass_p, stills_dir=stills_d, verbose=False)
        self.assertEqual(failures, [], f"Expected 0 failures, got {failures}")

    def test_bad_resolution_fails_qa(self):
        """Non-1080x1920 clip fails resolution check."""
        clip_p = self.work_dir / "bad_res_clip.mp4"
        self._create_synthetic_clip(clip_p, width=720, height=1280)

        failures = qa.check_clip_file(clip_p, verbose=False)
        self.assertIn("resolution 1080x1920", failures)

    def test_missing_audio_fails_qa(self):
        """Clip without an audio stream fails audio checks."""
        clip_p = self.work_dir / "silent_clip.mp4"
        self._create_synthetic_clip(clip_p, with_audio=False)

        failures = qa.check_clip_file(clip_p, verbose=False)
        self.assertIn("audio stream present", failures)

    def test_captions_outside_safe_zone_fails_qa(self):
        """Captions in bottom overlay (MarginV=1513) or out of bounds fail safe area check."""
        clip_p = self.work_dir / "caption_test_clip.mp4"
        self._create_synthetic_clip(clip_p)
        ass_p = self.work_dir / "bad_anchor_captions.ass"
        self._create_synthetic_ass(ass_p, margin_v=1513)  # old unsafe bottom overlay

        failures = qa.check_clip_file(clip_p, ass_path=ass_p, verbose=False)
        self.assertIn("captions safe-zone vertical alignment", failures)

    def test_captions_without_box_backdrop_fails_qa(self):
        """Captions missing valid BorderStyle backdrop fail contrast check."""
        clip_p = self.work_dir / "caption_nobox_clip.mp4"
        self._create_synthetic_clip(clip_p)
        ass_p = self.work_dir / "nobox_captions.ass"
        self._create_synthetic_ass(ass_p, margin_v=1180, border_style=0)  # BorderStyle=0 no box/outline

        failures = qa.check_clip_file(clip_p, ass_path=ass_p, verbose=False)
        self.assertIn("captions contrast box backdrop", failures)

    def test_edge_sliced_stills_fail_qa(self):
        """Stills with sliced headlines touch-tested by pin_edge_check fail QA."""
        clip_p = self.work_dir / "edge_slice_clip.mp4"
        self._create_synthetic_clip(clip_p)
        stills_d = self.work_dir / "stills_sliced"
        self._create_synthetic_stills(stills_d, sliced=True)

        failures = qa.check_clip_file(clip_p, stills_dir=stills_d, verbose=False)
        self.assertIn("no edge-sliced text in verification stills", failures)


if __name__ == "__main__":
    unittest.main()
