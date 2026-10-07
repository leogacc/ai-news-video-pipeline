#!/usr/bin/env python3
"""PRODUCER (visuals) — relevant b-roll per segment via a bounded loop:
X-post video (fxtwitter, trimmed <=8s) -> Pixabay video -> Pixabay photo
(Ken Burns at render) -> broadened query -> generated title card.
Cached by query. -> output/visuals.json
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


def pixabay_media(query: str, kind: str = "videos"):
    """kind = "videos" -> clips, "photos" -> stills (Ken Burns at render)."""
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return None
    if kind == "videos":
        endpoint, params = "https://pixabay.com/api/videos/", {
            "key": key, "q": query, "per_page": 3}
    else:
        endpoint, params = "https://pixabay.com/api/", {
            "key": key, "q": query, "per_page": 3,
            "image_type": "photo", "orientation": "vertical"}
    r = requests.get(endpoint, params=params, timeout=30)
    r.raise_for_status()
    for hit in r.json().get("hits", []):
        if kind == "videos":
            vids = hit.get("videos", {})
            for quality in ("medium", "small", "large"):
                if quality in vids:
                    return vids[quality]["url"]
        else:
            link = hit.get("largeImageURL") or hit.get("webformatURL")
            if link:
                return link
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


X_CLIP_MAX_SEC = 8  # third-party clips are trimmed short (fair-use heuristic)


def fxtwitter_clip(status_url: str, dest: Path) -> bool:
    """Download the video attached to an x.com post via the free fxtwitter
    API, trimmed to X_CLIP_MAX_SEC. Returns True on success."""
    import subprocess
    m = re.search(r"x\.com/([^/]+)/status/(\d+)", status_url)
    if not m:
        return False
    handle, sid = m.groups()
    d = requests.get(f"https://api.fxtwitter.com/{handle}/status/{sid}",
                     timeout=30).json()
    urls = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "url" and isinstance(v, str) and ".mp4" in v:
                    urls.append(v.split("?")[0])
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d.get("tweet", {}).get("media", {}))
    if not urls:
        return False
    tmp = dest.with_name(dest.stem + ".raw.mp4")
    download(urls[0], tmp)
    subprocess.run(["ffmpeg", "-y", "-i", str(tmp), "-t",
                    str(X_CLIP_MAX_SEC), "-c", "copy", str(dest)],
                   check=True, capture_output=True)
    tmp.unlink(missing_ok=True)
    return dest.exists() and dest.stat().st_size > 10_000


def main():
    import sys
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    script = json.loads((ROOT / "output" / "script.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    w, h = CFG[mode]["width"], CFG[mode]["height"]

    visuals = []

    # Pre-pass: for stories whose source is an x.com post, grab the post's
    # own video once via fxtwitter (most relevant visual possible).
    story_media = {}
    for sid, src in zip(script.get("story_ids", []),
                        script.get("sources", [])):
        url = src.get("url", "")
        if "x.com" in url and "/status/" in url and sid:
            dest = CACHE / f"xmedia_{slug(sid)}.mp4"
            if not dest.exists() or dest.stat().st_size < 10_000:
                try:
                    if fxtwitter_clip(url, dest):
                        print(f"[visuals] story {sid[:8]}: X post video -> clip")
                except Exception as e:
                    print(f"[visuals] fxtwitter failed for '{url[:60]}': {e}")
                    dest.unlink(missing_ok=True)
            if dest.exists() and dest.stat().st_size >= 10_000:
                story_media[sid] = str(dest)

    seen_x_stories = set()
    for i, seg in enumerate(script["segments"]):
        sid = seg.get("story_id")
        dur = timings[i]["duration"] + CFG["tts"]["segment_gap_sec"]
        # The story's own X video leads its first segment.
        if sid and sid in story_media and sid not in seen_x_stories:
            seen_x_stories.add(sid)
            visuals.append({"segment": i, "kind": "clip",
                            "path": story_media[sid], "duration": dur})
            print(f"[visuals] seg {i}: X post video -> clip")
            continue
        q = seg.get("broll") or "technology abstract"
        clip_dest = CACHE / f"{slug(q)}.mp4"
        photo_dest = CACHE / f"{slug(q)}.jpg"
        kind, path = None, None
        for cand in (clip_dest, photo_dest):
            if cand.exists() and cand.stat().st_size >= 10_000:
                kind = "clip" if cand.suffix == ".mp4" else "photo"
                path = str(cand)
                break
        if path is None:
            # Bounded relevance loop: specific video -> specific photo ->
            # broadened query video/photo -> title card.
            queries = [q, " ".join(q.split()[:2])]
            for qq in queries:
                for mkind, mdest in (("videos", clip_dest),
                                     ("photos", photo_dest)):
                    if path:
                        break
                    try:
                        url = pixabay_media(qq, mkind)
                    except Exception as e:
                        print(f"[visuals] pixabay {mkind} failed for "
                              f"'{qq}': {e}")
                        url = None
                    if not url and mkind == "videos":
                        try:
                            url = pexels_search(qq)
                        except Exception as e:
                            print(f"[visuals] pexels failed for '{qq}': {e}")
                    if url:
                        try:
                            download(url, mdest)
                            kind = "clip" if mkind == "videos" else "photo"
                            path = str(mdest)
                            print(f"[visuals] seg {i}: '{qq}' -> {kind}")
                        except Exception as e:
                            print(f"[visuals] download failed for '{qq}': {e}")
                            mdest.unlink(missing_ok=True)
        if path is None:
            path = str(ROOT / "output" / f"card_{i:02d}.png")
            title_card(script["title"], Path(path), w, h)
            kind = "card"
            print(f"[visuals] seg {i}: '{q}' -> title card fallback")
        visuals.append({"segment": i, "kind": kind, "path": path,
                        "duration": dur})
    (ROOT / "output" / "visuals.json").write_text(json.dumps(visuals, indent=2))
    print(f"[visuals] {len(visuals)} segments planned")


if __name__ == "__main__":
    main()
