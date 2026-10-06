#!/usr/bin/env python3
"""PRODUCER (visuals) — keyword b-roll via Pexels (Pixabay fallback), cached by
keyword. No match -> generated title card (Ken Burns zoom applied at render).
-> output/visuals.json
"""
import hashlib
import json
import os
import re
import textwrap
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
V = CFG["visuals"]
CACHE = ROOT / "cache" / "clips"
CACHE.mkdir(parents=True, exist_ok=True)


def slug(q: str) -> str:
    return hashlib.sha1(q.lower().encode()).hexdigest()[:12]


def pexels_search(query: str):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    r = requests.get(
        "https://api.pexels.com/videos/search",
        params={"query": query, "per_page": 3,
                "orientation": "portrait" if V["portrait_only"] else "landscape",
                "size": "medium"},
        headers={"Authorization": key},
        timeout=30)
    r.raise_for_status()
    for v in r.json().get("videos", []):
        files = [f for f in v.get("video_files", [])
                 if f.get("height", 0) >= 480 and f.get("link")]
        if not files:
            continue
        # smallest file that still clears 480p keeps downloads light
        files.sort(key=lambda f: f["height"])
        small = [f for f in files if f["height"] <= V["clip_max_height"]]
        return (small or files)[0]["link"]
    return None


def pixabay_search(query: str):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    r = requests.get(
        "https://pixabay.com/api/videos/",
        params={"key": key, "q": query, "per_page": 3},
        timeout=30)
    r.raise_for_status()
    for v in r.json().get("hits", []):
        vids = v.get("videos", {})
        for quality in ("medium", "small", "large"):
            if quality in vids:
                return vids[quality]["url"]
    return None


def download(url: str, dest: Path):
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


def title_card(text: str, dest: Path, w: int, h: int):
    """Fallback visual: dark gradient card with the story title."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (w, h), (12, 14, 22))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except Exception:
        font = small = ImageFont.load_default()
    d.text((w // 2, int(h * 0.38)), "AI NEWS", font=small, fill=(120, 180, 255),
           anchor="mm")
    wrapped = textwrap.fill(text, width=22)
    d.multiline_text((w // 2, int(h * 0.52)), wrapped, font=font, fill=(240, 244, 255),
                     anchor="mm", align="center", spacing=12)
    img.save(dest)


def main():
    import sys
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    script = json.loads((ROOT / "output" / "script.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    w, h = CFG[mode]["width"], CFG[mode]["height"]

    visuals = []
    for i, seg in enumerate(script["segments"]):
        q = seg.get("broll") or "technology abstract"
        dest = CACHE / f"{slug(q)}.mp4"
        kind = "clip"
        if not dest.exists() or dest.stat().st_size < 10_000:
            url = None
            for fn in (pexels_search, pixabay_search):
                try:
                    url = fn(q)
                except Exception as e:
                    print(f"[visuals] {fn.__name__} failed for '{q}': {e}")
                if url:
                    break
            if url:
                try:
                    download(url, dest)
                    print(f"[visuals] seg {i}: '{q}' -> clip")
                except Exception as e:
                    print(f"[visuals] download failed for '{q}': {e}")
                    dest.unlink(missing_ok=True)
            if not dest.exists():
                dest = ROOT / "output" / f"card_{i:02d}.png"
                title_card(script["title"], dest, w, h)
                kind = "card"
                print(f"[visuals] seg {i}: '{q}' -> title card fallback")
        visuals.append({
            "segment": i,
            "kind": kind,
            "path": str(dest),
            "duration": timings[i]["duration"] + CFG["tts"]["segment_gap_sec"],
        })
    (ROOT / "output" / "visuals.json").write_text(json.dumps(visuals, indent=2))
    print(f"[visuals] {len(visuals)} segments planned")


if __name__ == "__main__":
    main()
