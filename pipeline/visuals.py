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
    # A real User-Agent: thumb.wikimedia.org 403s generic clients.
    with requests.get(url, stream=True, timeout=120,
                      headers=COMMONS_UA) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)


COMMONS_UA = {"User-Agent":
              "ai-news-video-pipeline/1.0 (educational news digest)"}


def commons_image(subject: str):
    """Evidence shot from Wikimedia Commons (freely licensed): the specific
    thing named by `subject` (person, logo, landmark, product). Returns a
    direct jpg/png URL or None."""
    try:
        s = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "format": "json", "list": "search",
                    "srsearch": f"{subject} filetype:jpg",
                    "srnamespace": 6, "srlimit": 8},
            headers=COMMONS_UA, timeout=30).json()
        titles = [h["title"] for h in s.get("query", {}).get("search", [])]
        if not titles:
            return None
        ii = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "format": "json",
                    "prop": "imageinfo", "iiprop": "url|size",
                    "iiurlwidth": 1280, "titles": "|".join(titles)},
            headers=COMMONS_UA, timeout=30).json()
        for p in ii.get("query", {}).get("pages", {}).values():
            for info in p.get("imageinfo", []):
                u = info.get("thumburl") or info.get("url", "")
                if u.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
                    return u
    except Exception as e:
        print(f"[visuals] commons failed for '{subject}': {e}")
    return None


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


def fetch_trimmed_video(url: str, dest: Path) -> bool:
    """Download a video URL and trim to X_CLIP_MAX_SEC (fair-use heuristic)."""
    import subprocess
    tmp = dest.with_name(dest.stem + ".raw.mp4")
    download(url, tmp)
    subprocess.run(["ffmpeg", "-y", "-i", str(tmp), "-t",
                    str(X_CLIP_MAX_SEC), "-c", "copy", str(dest)],
                   check=True, capture_output=True)
    tmp.unlink(missing_ok=True)
    return dest.exists() and dest.stat().st_size > 10_000


def fxtwitter_mp4(status_url: str):
    """Resolve the direct mp4 URL of a video attached to an x.com post via
    the free fxtwitter API. Returns None if there is none."""
    m = re.search(r"x\.com/([^/]+)/status/(\d+)", status_url)
    if not m:
        return None
    handle, sid = m.groups()
    d = requests.get(f"https://api.fxtwitter.com/{handle}/status/{sid}",
                     timeout=30).json()
    urls = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "url" and isinstance(v, str) and ".mp4" in v:
                    urls.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(d.get("tweet", {}).get("media", {}))
    return urls[0] if urls else None


def website_media(article_url: str):
    """(kind, media_url) from the publisher's own page: og:video / twitter
    player stream first, then og:image / twitter:image. (None, None) if the
    page can't be fetched or declares no media."""
    if not article_url or "x.com" in article_url \
            or "news.google.com" in article_url:
        return None, None
    try:
        r = requests.get(
            article_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                                   "Chrome/126.0.0.0 Safari/537.36"},
            timeout=30)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        print(f"[visuals] article fetch failed for media: {e}")
        return None, None

    def meta(prop):
        m = re.search(r'<meta[^>]*?(?:property|name)="' + prop + r'"[^>]*?>',
                      html, re.I)
        if not m:
            return None
        c = re.search(r'content="([^"]+)"', m.group(0), re.I)
        return c.group(1) if c else None

    for prop in ("og:video", "twitter:player:stream"):
        u = meta(prop)
        if u and ".mp4" in u:
            return "clip", u
    for prop in ("og:image", "twitter:image"):
        u = meta(prop)
        if u and not u.lower().endswith(".svg"):
            return "photo", u
    return None, None


def main():
    import sys
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    script = json.loads((ROOT / "output" / "script.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    w, h = CFG[mode]["width"], CFG[mode]["height"]

    visuals = []

    # Pre-pass per story, in relevance order:
    #   1. the story's own X post video (x_media_url, or x.com story URL)
    #   2. the publisher's own page media (og:video / og:image)
    # Later segments fall through to the Pixabay loop below.
    story_assets = {}  # sid -> [(kind, local_path), ...]
    for sid, src in zip(script.get("story_ids", []),
                        script.get("sources", [])):
        if not sid:
            continue
        assets = []
        xurl = src.get("x_media_url") or ""
        if not xurl:
            u = src.get("url", "")
            xurl = u if ("x.com" in u and "/status/" in u) else ""
        if xurl:
            dest = CACHE / f"xmedia_{slug(sid)}.mp4"
            try:
                if dest.stat().st_size < 10_000:
                    raise FileNotFoundError
            except FileNotFoundError:
                try:
                    mp4 = fxtwitter_mp4(xurl)
                    if mp4 and fetch_trimmed_video(mp4, dest):
                        print(f"[visuals] story {sid[:8]}: X post video -> clip")
                    else:
                        dest.unlink(missing_ok=True)
                except Exception as e:
                    print(f"[visuals] X video failed for '{xurl[:60]}': {e}")
                    dest.unlink(missing_ok=True)
            if dest.exists() and dest.stat().st_size >= 10_000:
                assets.append(("clip", str(dest)))
        wkind, wurl = website_media(src.get("url", ""))
        if wurl:
            ext = ".mp4" if wkind == "clip" else ".jpg"
            dest = CACHE / f"sitemedia_{slug(sid)}{ext}"
            try:
                if dest.stat().st_size < 10_000:
                    raise FileNotFoundError
            except FileNotFoundError:
                try:
                    if wkind == "clip":
                        ok = fetch_trimmed_video(wurl, dest)
                    else:
                        download(wurl, dest)
                        ok = dest.stat().st_size > 10_000
                    if ok:
                        print(f"[visuals] story {sid[:8]}: publisher {wkind} -> {wkind}")
                    else:
                        dest.unlink(missing_ok=True)
                except Exception as e:
                    print(f"[visuals] publisher media failed for "
                          f"'{src.get('url', '')[:60]}': {e}")
                    dest.unlink(missing_ok=True)
            if dest.exists() and dest.stat().st_size >= 10_000:
                assets.append((wkind, str(dest)))
        if assets:
            story_assets[sid] = assets

    story_seg_n = {}
    for i, seg in enumerate(script["segments"]):
        sid = seg.get("story_id")
        dur = timings[i]["duration"] + CFG["tts"]["segment_gap_sec"]
        seg_kind = seg.get("kind", "story")  # hook | headlines | story
        vtype = seg.get("visual_type", "illustrative")  # evidence | illustrative
        # Story-owned media first, in priority order across its segments.
        assets = story_assets.get(sid, []) if sid else []
        n = story_seg_n.get(sid, 0)
        if n < len(assets):
            story_seg_n[sid] = n + 1
            kind, path = assets[n]
            visuals.append({"segment": i, "kind": kind, "path": path,
                            "duration": dur, "seg_kind": seg_kind})
            print(f"[visuals] seg {i}: story-owned {kind} -> {kind}")
            continue
        story_seg_n[sid] = n + 1
        q = seg.get("broll") or "technology abstract"
        clip_dest = CACHE / f"{slug(q)}.mp4"
        photo_dest = CACHE / f"{slug(q)}.jpg"
        kind, path = None, None
        for cand in (clip_dest, photo_dest):
            if cand.exists() and cand.stat().st_size >= 10_000:
                kind = "clip" if cand.suffix == ".mp4" else "photo"
                path = str(cand)
                break
        # Evidence tier: the visual IS the thing being discussed (person,
        # logo, landmark, product) — Wikimedia Commons before stock.
        if path is None and vtype == "evidence" and seg.get("visual_subject"):
            subj = seg["visual_subject"]
            try:
                url = commons_image(subj)
            except Exception as e:
                print(f"[visuals] commons failed for '{subj}': {e}")
                url = None
            if url:
                try:
                    dest = CACHE / f"commons_{slug(subj)}.jpg"
                    download(url, dest)
                    if dest.stat().st_size > 10_000:
                        kind, path = "photo", str(dest)
                        print(f"[visuals] seg {i}: commons '{subj}' -> photo")
                    else:
                        dest.unlink(missing_ok=True)
                except Exception as e:
                    print(f"[visuals] commons download failed for "
                          f"'{subj}': {e}")
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
                        "duration": dur, "seg_kind": seg_kind})
    (ROOT / "output" / "visuals.json").write_text(json.dumps(visuals, indent=2))
    print(f"[visuals] {len(visuals)} segments planned")


if __name__ == "__main__":
    main()
