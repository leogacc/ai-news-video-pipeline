#!/usr/bin/env python3
"""Remotion Animation Engine Python Bridge (v2026.11.06.4).

Provides broadcast-grade programmatic animation generation for non-visual and
abstract finds (research papers, benchmark breakthroughs, multi-agent architectures).
All animations render to 1080x1920 vertical H.264 MP4 videos matching the channel's
terminal aesthetic (#000000 pure black, #39FF14 neon green, tabular figures).

Available compositions:
- BenchmarkLadder: Comparative horizontal bar charts with SOTA highlights and delta badges.
- ArchitectureDiagram: Multi-agent pipelines, reasoning flows, and traveling packet pulses.
- KineticMetricCounter: Rapid tabular number tickers, glowing progress gauges, and metric tiles.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

ANIMATIONS_DIR = Path(__file__).resolve().parent / "animations"
RENDER_MJS = ANIMATIONS_DIR / "render.mjs"
NODE_BIN = shutil.which("node") or "/usr/local/bin/node"

SUPPORTED_COMPOSITIONS = {
    "BenchmarkLadder",
    "ArchitectureDiagram",
    "KineticMetricCounter",
    "TweetCard3D",
    "PersistentHookBanner",
    "DocumentZoom",
}


def render_animation(
    composition: str,
    props: Dict[str, Any],
    output_path: Union[str, Path],
    duration_frames: Optional[int] = None,
    fps: int = 30,
    crf: int = 18,
    timeout: int = 120,
) -> Path:
    """Renders a Remotion composition to an MP4 video file.

    Args:
        composition: Name of the registered composition (e.g., 'BenchmarkLadder').
        props: Dictionary of props passed to the React composition.
        output_path: Destination path for the rendered MP4 file.
        duration_frames: Optional override for duration in frames.
        fps: Target framerate (default 30fps).
        crf: Constant Rate Factor for H.264 (default 18 for visually lossless).
        timeout: Subprocess timeout in seconds.

    Returns:
        Path to the successfully rendered MP4 video.

    Raises:
        ValueError: If the composition is unrecognized.
        FileNotFoundError: If node or render.mjs cannot be found.
        RuntimeError: If rendering fails.
    """
    if composition not in SUPPORTED_COMPOSITIONS:
        raise ValueError(
            f"Unsupported composition '{composition}'. Must be one of: {sorted(SUPPORTED_COMPOSITIONS)}"
        )

    if not RENDER_MJS.exists():
        raise FileNotFoundError(f"Remotion CLI renderer not found at {RENDER_MJS}")

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Write props to a temporary JSON file to avoid CLI escaping issues
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(props, tf)
        tmp_props_path = tf.name

    try:
        cmd = [
            NODE_BIN,
            str(RENDER_MJS),
            "--composition",
            composition,
            "--props",
            tmp_props_path,
            "--out",
            str(out_file),
            "--fps",
            str(fps),
            "--crf",
            str(crf),
        ]
        if duration_frames:
            cmd.extend(["--durationInFrames", str(duration_frames)])

        logger.info("Executing Remotion render: %s -> %s", composition, out_file)
        res = subprocess.run(
            cmd,
            cwd=str(ANIMATIONS_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if res.returncode != 0:
            err_msg = (res.stderr or res.stdout or "").strip()
            logger.error("Remotion render failed with exit code %d:\n%s", res.returncode, err_msg)
            raise RuntimeError(f"Remotion render failed (code {res.returncode}): {err_msg}")

        if not out_file.exists() or out_file.stat().st_size == 0:
            raise RuntimeError(f"Remotion completed but output file is missing or empty: {out_file}")

        logger.info("Remotion render complete (%d bytes) -> %s", out_file.stat().st_size, out_file)
        return out_file

    finally:
        if os.path.exists(tmp_props_path):
            try:
                os.remove(tmp_props_path)
            except OSError:
                pass


def render_benchmark_ladder(
    title: str,
    benchmark_name: str,
    items: List[Dict[str, Any]],
    output_path: Union[str, Path],
    subtitle: Optional[str] = None,
    metric_unit: str = "%",
    delta_callout: Optional[str] = None,
    source: Optional[str] = None,
    duration_frames: int = 120,
) -> Path:
    """Renders a 1080x1920 Benchmark Ladder MP4 video."""
    props: Dict[str, Any] = {
        "title": title,
        "benchmarkName": benchmark_name,
        "items": items,
        "metricUnit": metric_unit,
    }
    if subtitle:
        props["subtitle"] = subtitle
    if delta_callout:
        props["deltaCallout"] = delta_callout
    if source:
        props["source"] = source

    return render_animation(
        composition="BenchmarkLadder",
        props=props,
        output_path=output_path,
        duration_frames=duration_frames,
    )


def render_architecture_diagram(
    title: str,
    nodes: List[Dict[str, Any]],
    output_path: Union[str, Path],
    subtitle: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    duration_frames: int = 150,
) -> Path:
    """Renders a 1080x1920 Architecture Flow Diagram MP4 video."""
    props: Dict[str, Any] = {
        "title": title,
        "nodes": nodes,
    }
    if subtitle:
        props["subtitle"] = subtitle
    if category:
        props["category"] = category
    if source:
        props["source"] = source

    return render_animation(
        composition="ArchitectureDiagram",
        props=props,
        output_path=output_path,
        duration_frames=duration_frames,
    )


def render_kinetic_counter(
    title: str,
    target_value: float,
    output_path: Union[str, Path],
    subtitle: Optional[str] = None,
    badge: Optional[str] = None,
    metric_label: Optional[str] = None,
    prefix: str = "",
    suffix: str = "",
    decimals: int = 0,
    delta_callout: Optional[str] = None,
    sub_metrics: Optional[List[Dict[str, Any]]] = None,
    source: Optional[str] = None,
    duration_frames: int = 120,
) -> Path:
    """Renders a 1080x1920 Kinetic Metric Counter MP4 video."""
    props: Dict[str, Any] = {
        "title": title,
        "targetValue": target_value,
        "prefix": prefix,
        "suffix": suffix,
        "decimals": decimals,
    }
    if subtitle:
        props["subtitle"] = subtitle
    if badge:
        props["badge"] = badge
    if metric_label:
        props["metricLabel"] = metric_label
    if delta_callout:
        props["deltaCallout"] = delta_callout
    if sub_metrics:
        props["subMetrics"] = sub_metrics
    if source:
        props["source"] = source

    return render_animation(
        composition="KineticMetricCounter",
        props=props,
        output_path=output_path,
        duration_frames=duration_frames,
    )


def render_tweet_card_3d(
    card_image_path: Union[str, Path],
    output_path: Union[str, Path],
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    badge: Optional[str] = None,
    source: Optional[str] = None,
    highlight_words: Optional[List[str]] = None,
    duration_frames: int = 120,
) -> Path:
    """Renders a 1080x1920 3D perspective TweetCard MP4 video with entry tilt and animated highlighter."""
    import base64

    card_path = Path(card_image_path).resolve()
    if not card_path.exists():
        raise FileNotFoundError(f"Card image not found at {card_path}")

    with open(card_path, "rb") as f:
        data_b64 = base64.b64encode(f.read()).decode("ascii")
    card_src = f"data:image/png;base64,{data_b64}"

    props: Dict[str, Any] = {
        "cardSrc": card_src,
    }
    if title:
        props["title"] = title
    if subtitle:
        props["subtitle"] = subtitle
    if badge:
        props["badge"] = badge
    if source:
        props["source"] = source
    if highlight_words:
        props["highlightWords"] = highlight_words

    return render_animation(
        composition="TweetCard3D",
        props=props,
        output_path=output_path,
        duration_frames=duration_frames,
    )


def render_document_zoom(
    source_name: str,
    headline: str,
    quote_text: str,
    output_path: Union[str, Path],
    badge: str = "VERIFIED DISPATCH",
    source: str = "Source: Primary Source Investigation",
    image_src: str = "",
    duration_frames: int = 90,
) -> Path:
    """Renders a DocumentZoom composition zooming onto an article quote with highlighter sweep."""
    props: Dict[str, Any] = {
        "sourceName": source_name,
        "headline": headline,
        "quoteText": quote_text,
        "badge": badge,
        "source": source,
        "imageSrc": image_src,
    }
    return render_animation(
        composition="DocumentZoom",
        props=props,
        output_path=output_path,
        duration_frames=duration_frames,
    )


if __name__ == "__main__":
    import sys

    print("Remotion Animation Engine Bridge (Python)")
    if len(sys.argv) < 2:
        print("Usage: python3 -m pipeline.animations [test]")
        sys.exit(0)

    if sys.argv[1] == "test":
        test_out = Path("/tmp/pipeline_test_ladder.mp4")
        print(f"Running sample render to {test_out}...")
        render_benchmark_ladder(
            title="SWE-BENCH REASONING LEAP",
            benchmark_name="SWE-bench Verified",
            items=[
                {"label": "o1-preview", "value": 84.6, "highlight": True, "badge": "NEW SOTA"},
                {"label": "Claude 3.5 Sonnet", "value": 72.8, "baseline": True},
                {"label": "GPT-4o", "value": 68.4, "baseline": True},
            ],
            output_path=test_out,
            duration_frames=45,
        )
        print(f"Success! Output file: {test_out} ({test_out.stat().st_size} bytes)")
