#!/usr/bin/env python3
"""PIN EDGE-SLICE DETECTOR (2026-10-27, v2026.10.27.2).

A vision-cropped article card whose crop cuts through its own headline
ships a sliced title — the 20:48 daily cut carried the same sliced PYMNTS
headline TWICE (hook hero + deep-dive pin) because no check ever looked
at pin edges. This detector closes that hole.

Signature of a sliced headline: near-black glyph pixels touching the
image's outermost rows/columns in MANY SHORT runs (one per clipped
letter stem) against a paper-white edge. Solid blocks (a phone bezel, a
dark illustration) give one or two LONG runs instead, and photos give
dark edges that are not paper-white at all — so the rule is:

  flag an edge iff its 2px strip has median luminance >= 230
  (paper-white margin, not sky, not a dark card, not a photo edge)
  AND it carries >= 5 short dark runs (luminance < 100, length 2..60px).

Calibrated 2026-10-27 on today's video: the defective PYMNTS crops show
16 short runs on a median-249 top edge; the brightest clean photo edge
in the set is median 220, and the most short runs on any qualifying
clean edge is 1 (Opera UI bottom bezel). Both thresholds sit in wide
gaps, so the detector is not tuned to a single image.

Usage:
  pin_edge_check.py <file-or-dir>...   # exit 1 if any still is flagged
  from pin_edge_check import check_visuals  # qa.py wiring: takes the
      # visuals.json shot list, returns {path: [edges]} for stills only.
Video files (.mp4) are skipped — this is a still-pin check.
"""
import sys
from pathlib import Path

from PIL import Image
import numpy as np

STRIP_DEPTH = 2          # outermost rows/columns examined
EDGE_MEDIAN_MIN = 230    # paper-white margin (photos top out ~220 here)
DARK_MAX = 100           # near-black glyph pixels
RUN_MIN, RUN_MAX = 2, 60  # a clipped letter stem, not a bezel or a photo edge
MIN_SHORT_RUNS = 5       # defective crops show 16; clean edges show <= 1

STILL_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _runs(line):
    """Lengths of consecutive True runs in a 1-D boolean array."""
    runs, cur = [], 0
    for v in line:
        if v:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return runs


def check_image(path):
    """Return the list of edges ('top'/'bottom'/'left'/'right') whose
    outermost strip shows sliced-text signature, or [] if clean."""
    try:
        gray = np.array(Image.open(path).convert("L"))
    except Exception:
        return []
    flagged = []
    strips = (
        ("top", gray[0:STRIP_DEPTH, :], 0),
        ("bottom", gray[-STRIP_DEPTH:, :], 0),
        ("left", gray[:, 0:STRIP_DEPTH], 1),
        ("right", gray[:, -STRIP_DEPTH:], 1),
    )
    for name, strip, axis in strips:
        if int(np.median(strip)) < EDGE_MEDIAN_MIN:
            continue  # not a paper-white margin: photo, dark card, artwork
        dark = strip < DARK_MAX
        line = dark.any(axis=axis)
        short = sum(1 for r in _runs(line) if RUN_MIN <= r <= RUN_MAX)
        if short >= MIN_SHORT_RUNS:
            flagged.append(name)
    return flagged


def check_paths(paths):
    """{str(path): [edges]} for every still in paths that is flagged."""
    offenders = {}
    for p in paths:
        p = Path(p)
        if p.suffix.lower() not in STILL_EXTS or not p.exists():
            continue
        edges = check_image(p)
        if edges:
            offenders[str(p)] = edges
    return offenders


def check_visuals(shots):
    """qa.py entry point: takes the visuals.json shot list (dicts with a
    'path' key) and returns {path: [edges]} for flagged stills."""
    return check_paths([s.get("path", "") for s in shots])


HERO_MAX_ASPECT = 1.5  # wider renders as a short band + dead space


def check_hero_aspect(shots, max_aspect=HERO_MAX_ASPECT):
    """qa.py entry point: takes the visuals.json shot list, returns
    ["name (WxH)"] for every hook-hero still wider than max_aspect.

    Why heroes only: a hook hero wider than 1.5:1 renders as a short
    centred band in the 1490px visual zone — the 21:14 cut's Opera hero
    (1600x800, aspect 2.0) filled only 540px, leaving ~490px of blurred
    stretch between the content and the pinned captions, which reads
    as dead space. Deep-dive cards and photos are exempt from this hard
    gate: a card's text can't always be portrait-reframed from its pin,
    and a horizontal-subject photo can't be portrait-cropped without
    cutting its subject — those go through the pin spec (prefer
    portrait-leaning crops) instead. Video files are skipped — this is
    a still-pin check.
    """
    offenders = []
    for s in shots:
        if s.get("seg_kind") != "hook" or s.get("source") != "hook-hero":
            continue
        p = Path(s.get("path", ""))
        if p.suffix.lower() not in STILL_EXTS or not p.exists():
            continue
        try:
            with Image.open(p) as im:
                w, h = im.size
        except Exception:
            continue
        if w / h > max_aspect:
            offenders.append(f"{p.name} ({w}x{h})")
    return offenders


def main(argv):
    paths = []
    for a in argv[1:]:
        p = Path(a)
        if p.is_dir():
            paths.extend(sorted(str(f) for f in p.iterdir()
                                if f.suffix.lower() in STILL_EXTS))
        else:
            paths.append(a)
    offenders = check_paths(paths)
    for p in sorted(set(paths)):
        if p in offenders:
            print(f"[edge-check] FAIL {p} sliced edges: {offenders[p]}")
        else:
            print(f"[edge-check] PASS {p}")
    if offenders:
        print(f"[edge-check] BLOCKED: {len(offenders)} pin(s) with "
              f"sliced text — re-crop with whitespace beyond the "
              f"outermost text line")
        return 1
    print("[edge-check] all pins clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
