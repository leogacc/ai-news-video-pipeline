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
import time
from pathlib import Path

from PIL import Image
import numpy as np

import requests
import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())
V = CFG["visuals"]
CACHE = ROOT / "cache" / "clips"
CACHE.mkdir(parents=True, exist_ok=True)
# Agent-verified pins: searched and relevance-checked by the research
# loop (never blind search). Outranks every other source.
VCACHE = ROOT / "cache" / "verified"
VCACHE.mkdir(parents=True, exist_ok=True)


def _build_hook_pairs(script, mode="daily"):
    """Stack each story's person photo over its company logo.

    Saves pipeline/cache/verified/hook_pair_<story_id>.png for the 5
    headline hooks. Person photo on top (240px), logo underneath (112px),
    12px gap. Stories with no person photo get a logo-only pair
    (2026-10-12: person-less stories used to fall back to a generic
    screenshot in the hook — the logo is the correct hook visual).
    Skips stories with neither person nor logo.

    Landscape mode (2026-10-13): person LEFT, logo RIGHT, side by side —
    the natural 16:9 arrangement. Saved as hook_pair_<sid>_landscape.png
    so the two orientations never collide in the shared cache.
    """
    from PIL import Image
    story_ids = script.get("story_ids", [])
    story_people = script.get("story_people", {})
    story_icons = script.get("story_icons", {})
    for sid in story_ids:
        out = ROOT / "cache" / "verified" / f"hook_pair_{sid}.png"
        if mode == "landscape":
            out = ROOT / "cache" / "verified" / f"hook_pair_{sid}_landscape.png"
        if out.exists():
            continue
        pf = story_people.get(sid, "")
        pp = ROOT / "cache" / "verified" / pf if pf else None
        person = None
        if pp and pp.exists():
            person = Image.open(pp).convert("RGB")
            ph = 300 if mode == "landscape" else 240
            r = ph / person.height
            person = person.resize((int(person.width * r), ph),
                                   Image.LANCZOS)
        logo = None
        lspec = story_icons.get(sid)
        if lspec:
            lp = ROOT / "cache" / "verified" / lspec
            if lp.exists():
                logo = Image.open(lp)
                if logo.mode == "RGBA":
                    bg = Image.new("RGB", logo.size, (0, 0, 0))
                    bg.paste(logo, mask=logo.split()[3])
                    logo = bg
                else:
                    logo = logo.convert("RGB")
                # 2026-10-12: invert dark marks — a black logo on the
                # pair's black background would be invisible. Sample only
                # the opaque mark pixels, not the black background.
                _rgba = Image.open(lp).convert("RGBA")
                _a = _rgba.split()[3]
                _lum = _rgba.convert("L")
                _mark = [l for l, a in zip(_lum.getdata(), _a.getdata())
                         if a > 10]
                if _mark and sum(_mark) / len(_mark) < 80:
                    from PIL import ImageOps
                    logo = ImageOps.invert(logo)
                r2 = 112 / logo.height
                logo = logo.resize((min(int(logo.width * r2), 400), 112),
                                   Image.LANCZOS)
        if person is None and logo is None:
            print(f"[visuals] hook pair SKIP {sid}: no person photo, no logo")
            continue
        if person is None:
            # Logo-only pair for person-less stories.
            composed = logo
            print(f"[visuals] hook pair built (logo-only): {out.name}")
        elif logo is None:
            composed = person
        elif mode == "landscape":
            # Side-by-side (2026-10-13): person left, logo right, 24px gap,
            # vertically centered on the taller of the two.
            gap = 24
            ch = max(person.height, logo.height)
            cw = person.width + gap + logo.width
            composed = Image.new("RGB", (cw, ch), (0, 0, 0))
            composed.paste(person, (0, (ch - person.height) // 2))
            composed.paste(logo, (person.width + gap,
                                  (ch - logo.height) // 2))
        else:
            cw = max(person.width, logo.width)
            ch = person.height + 12 + logo.height
            composed = Image.new("RGB", (cw, ch), (0, 0, 0))
            composed.paste(person, ((cw - person.width) // 2, 0))
            composed.paste(logo, ((cw - logo.width) // 2, person.height + 12))
        composed.save(out)
        if person is not None:
            print(f"[visuals] hook pair built: {out.name}")



def slug(q: str) -> str:
    return hashlib.sha1(q.lower().encode()).hexdigest()[:12]


def _is_text_card(path: str) -> bool:
    """Detect pre-rendered text cards masquerading as photo pins (2026-10-10).

    A previous worker pinned text-on-black graphics as 'verified' photos;
    they rendered as mid-screen text without any analytical animation.
    Heuristic: >75% of pixels very dark = text card, not a photo.
    Logos (logo_*.png) are exempt — they're supposed to be graphics.
    Eye-verified logo pins (2026-10-10) are also exempt via hash whitelist.
    """
    # Eye-verified legitimate pins (ICO logo, Philly PD, Anthropic, SoftBank)
    VERIFIED_HASHES = {
        "a7be0691b0d0ffbdfa75b967208900ad75f1ec2a9cb0bba4ae29a87a36c1c277",
        "840dc98365d33493468acbc50593c6732157e3eddf85045ef699bef58898341f",
        "20bb768df8ef3d79ecdbad6599ac1e4444967a40bcfda678a224f4a95c289a57",
        "c36851ddeb9a12db8cb12f5f8027e1468b0d524cb259b83d308dc0000d166780",
    }
    try:
        if Path(path).name.startswith("logo_"):
            return False
        import hashlib
        h = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if h in VERIFIED_HASHES:
            return False
        im = Image.open(path).convert("RGB")
        arr = np.array(im)
        dark = (arr.mean(axis=2) < 30).mean()
        return dark > 0.75
    except Exception:
        return False


# --- Semantic clip library (2026-10-09): match-then-generate, lite. ---
# Reuses previously fetched stock clips for semantically similar queries
# instead of hitting the network for near-duplicate searches. Token-overlap
# scoring (>= 0.6 with >= 2 shared content tokens); illustrative tier only
# — evidence shots never come from here, and verified pins always outrank it.
LIBCAT = VCACHE / "clip_catalog.json"
_LIB_STOP = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "with",
             "and", "or", "is", "are", "was", "were", "be", "by", "as",
             "from", "that", "this", "it", "its", "video", "videos",
             "footage", "clip", "clips", "photo", "photos", "image",
             "images", "showing", "show", "shows", "shot", "background"}


def _lib_tokens(q: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", q.lower())
            if t not in _LIB_STOP}


def _load_catalog() -> dict:
    try:
        return json.loads(LIBCAT.read_text())
    except Exception:
        return {}


def _save_catalog(cat: dict):
    LIBCAT.write_text(json.dumps(cat, indent=1))


def library_register(query: str, kind: str, path: Path):
    """Remember a fetched stock clip under its query for future reuse."""
    cat = _load_catalog()
    cat[slug(query)] = {"query": query, "tokens": sorted(_lib_tokens(query)),
                        "kind": kind, "path": str(path)}
    _save_catalog(cat)


def library_match(query: str, prev_path: str = None):
    """(kind, path) of the best catalog clip for a similar query, or None.
    Skips prev_path so two adjacent shots never freeze on one clip."""
    qt = _lib_tokens(query)
    if not qt:
        return None
    best, best_score = None, 0.0
    for e in _load_catalog().values():
        p = Path(e["path"])
        if not p.exists() or p.stat().st_size < 10_000:
            continue
        if prev_path and str(p) == str(prev_path):
            continue
        inter = qt & set(e.get("tokens", []))
        if len(inter) < 2:
            continue
        score = len(inter) / len(qt)
        if score >= 0.6 and score > best_score:
            best, best_score = (e["kind"], str(p)), score
    if best:
        print(f"[visuals] clip-library: '{query}' -> {Path(best[1]).name} "
              f"(overlap {best_score:.2f})")
    return best


# --- QA-quarantine retry support (2026-10-09). ---
# On a quarantine retry, run.py sets VISUALS_BAN to the slugs of the stock
# clips used in the failed render and VISUALS_RETRY=1: banned files are
# deleted so they re-fetch, and searches return their 2nd hit instead of
# the 1st — the retry genuinely shows different clips.
def _banned_slugs() -> set:
    return {s for s in os.environ.get("VISUALS_BAN", "").split(",") if s}


def _retry_mode() -> bool:
    return os.environ.get("VISUALS_RETRY") == "1"


def _image_has_content(path: Path) -> bool:
    """Reject degenerate images (uniform black/white squares) — a logo
    fetcher once put a corporate flowchart and black squares on screen
    as 'logos', so even verified pins get a sanity check."""
    try:
        from PIL import Image, ImageStat
        st = ImageStat.Stat(Image.open(path).convert("RGB"))
        return sum(st.var) > 50
    except Exception:
        return False


def verified_logo(company: str):
    """Logo overlay source: ONLY an agent-verified pin. The research loop
    web-searches the company's official logo, eyeball-verifies it IS the
    mark (not a diagram, photo, or article), and pins it to
    cache/verified/logo_{company}.png. No pin -> no overlay (honest miss),
    never a blind fetch: Commons sourcing once shipped a flowchart and
    black squares as 'logos', and Commons is banned from the pipeline
    entirely per the 2026-10-08 sourcing policy."""
    safe = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
    dest = VCACHE / f"logo_{safe}.png"
    if dest.exists() and dest.stat().st_size > 2000 \
            and _image_has_content(dest):
        return dest
    return None


# Logo-overlay allowlist: the overlay company must be the shot's visual
# subject (or its product). Story-level tagging ("story is about OpenAI" ->
# OpenAI logo on a Wikimedia article shot) is exactly the bug this blocks.
_LOGO_ALIASES = {
    "openai": {"openai", "chatgpt", "gpt4", "gpt5", "sora", "dalle", "textgrain"},
    "anthropic": {"anthropic", "claude", "haiku", "opus", "sonnet"},
    "google": {"google", "gemini", "synthid", "deepmind", "veo", "notebooklm",
               "projectastra"},
    "x": {"xai", "grok"},
    "meta": {"meta", "llama", "facebook", "instagram", "whatsapp"},
    "microsoft": {"microsoft", "copilot"},
    "nvidia": {"nvidia"},
    "apple": {"apple"},
    "spacex": {"spacex"},
}


def logo_allowed(company: str, subject: str, visual_type: str) -> bool:
    """True only if `company`'s logo belongs on this shot: the shot must be
    evidence (never illustrative) whose visual_subject names the company or
    one of its products."""
    if visual_type == "illustrative" or not company or not subject:
        return False
    co = re.sub(r"[^a-z0-9]", "", company.lower())
    aliases = _LOGO_ALIASES.get(co, {co})
    tokens = re.findall(r"[a-z0-9]+", subject.lower())
    for alias in aliases:
        for tok in tokens:
            if alias == tok:
                return True
            # substring only for longer aliases: "x" must never match
            # "wikimedia", "gpt" must never match "chatgpt"-less strings.
            if len(alias) >= 4 and (alias in tok or tok in alias):
                return True
    return False


def pexels_search(query: str, offset: int = 0):
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
    cands = []
    for v in r.json().get("videos", []):
        files = [f for f in v.get("video_files", [])
                 if f.get("height", 0) >= 480 and f.get("link")]
        if not files:
            continue
        # smallest file that still clears 480p keeps downloads light
        files.sort(key=lambda f: f["height"])
        small = [f for f in files if f["height"] <= V["clip_max_height"]]
        cands.append((small or files)[0]["link"])
    return cands[offset] if offset < len(cands) else None


def pixabay_media(query: str, kind: str = "videos", offset: int = 0):
    """kind = "videos" -> clips, "photos" -> stills (Ken Burns at render).
    offset picks the Nth search hit (quarantine retries take the 2nd)."""
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
    cands = []
    for hit in r.json().get("hits", []):
        if kind == "videos":
            vids = hit.get("videos", {})
            for quality in ("medium", "small", "large"):
                if quality in vids:
                    cands.append(vids[quality]["url"])
                    break
        else:
            link = hit.get("largeImageURL") or hit.get("webformatURL")
            if link:
                cands.append(link)
    return cands[offset] if offset < len(cands) else None


def download(url: str, dest: Path):
    # A real User-Agent: some hosts 403 generic clients.
    with requests.get(url, stream=True, timeout=120,
                      headers={"User-Agent": "ai-news-video-pipeline/1.0"}) as r:
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
    page can't be fetched or declares no media.

    (2026-10-11, user: generic aggregator URLs like aiagentstore.ai/ai-agent-news/today
    serve stock og:images that get reused across stories — reject listing pages,
    only fetch media from specific article URLs.)
    """
    if not article_url or "x.com" in article_url \
            or "news.google.com" in article_url:
        return None, None
    # Reject generic listing/aggregator pages — their og:image is stock,
    # not specific to the story.
    low = article_url.lower().rstrip("/")
    listing_patterns = (
        "/today", "/news", "/latest", "/headlines", "/top-stories",
        "/breaking", "/feed", "/articles", "/stories",
    )
    path = low.split("://", 1)[-1].split("/", 1)
    # Bare domain (homepage) or path ending in a listing slug
    if len(path) == 1 or any(low.endswith(p) for p in listing_patterns):
        print(f"[visuals] rejecting generic listing URL for story-owned "
              f"media: {article_url[:60]}")
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


_FACE_MODEL = ROOT / "cache" / "models" / "face_yunet.onnx"


def detect_face(path):
    """Largest face center as (fx, fy) in 0..1, measured in the
    center-cropped 9:16 region — i.e. what the final frame shows.
    None when no face is found. Uses OpenCV's YuNet DNN detector."""
    try:
        import cv2
        img = cv2.imread(str(path))
        if img is None or not _FACE_MODEL.exists():
            return None
        H, W = img.shape[:2]
        ratio = 9 / 16
        if W / H > ratio:  # wider than 9:16 -> crop sides
            cw = int(H * ratio)
            x0 = (W - cw) // 2
            crop = img[:, x0:x0 + cw]
        else:  # taller -> crop top/bottom
            ch = int(W / ratio)
            y0 = (H - ch) // 2
            crop = img[y0:y0 + ch, :]
        ch, cw = crop.shape[:2]
        det = cv2.FaceDetectorYN_create(str(_FACE_MODEL), "",
                                        (cw, ch), 0.5, 0.3, 5000)
        _, faces = det.detect(crop)
        if faces is None or len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])[:4]
        return [round(float(x + w / 2) / cw, 3),
                round(float(y + h / 2) / ch, 3)]
    except Exception as e:
        print(f"[visuals] face detect failed for '{path}': {e}")
        return None


def download_retry(url: str, dest: Path, tries: int = 4) -> bool:
    """Download with exponential backoff (some hosts rate-limit with
    HTTP 429; the file is usually fine a few seconds later)."""
    for attempt in range(tries):
        try:
            download(url, dest)
            if dest.stat().st_size > 2000:
                return True
            dest.unlink(missing_ok=True)
            return False
        except Exception as e:
            wait = 2 ** attempt
            print(f"[visuals] download attempt {attempt + 1}/{tries} failed "
                  f"({e}); retrying in {wait}s")
            time.sleep(wait)
    return False


def clip_review_strip(clip: Path, idx: int):
    """3 frames (25/50/75%) tiled into output/clip_review/ for the frame
    review step — a single contact-sheet frame can't judge a clip."""
    try:
        import subprocess
        from PIL import Image
        d = ROOT / "output" / "clip_review"
        d.mkdir(parents=True, exist_ok=True)
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(clip)],
            capture_output=True, text=True).stdout.strip() or 1)
        frames = []
        for frac in (0.25, 0.5, 0.75):
            fp = d / f"_{idx}_{int(frac*100)}.png"
            subprocess.run(["/usr/bin/ffmpeg", "-y", "-v", "error",
                            "-ss", f"{dur*frac:.2f}", "-i", str(clip),
                            "-frames:v", "1", str(fp)], check=True)
            im = Image.open(fp).convert("RGB")
            im.thumbnail((240, 240), Image.LANCZOS)
            frames.append(im)
            fp.unlink()
        strip = Image.new("RGB",
                          (sum(f.width for f in frames) + 20, frames[0].height),
                          (15, 15, 15))
        x = 0
        for f in frames:
            strip.paste(f, (x, 0))
            x += f.width + 10
        strip.save(d / f"clip_{idx:02d}.jpg", quality=85)
        print(f"[visuals] shot {idx}: clip review strip saved")
    except Exception as e:
        print(f"[visuals] clip strip failed: {e}")


def _is_verification_page(path: Path) -> bool:
    """Detect bot-verification/CAPTCHA pages in screenshots (2026-10-11).

    Root-cause fix (user): blacklist domains was a bandaid — ANY site can
    serve a verification wall. Scan the screenshot content instead.

    Verification pages vs article pages:
    - Verification: mostly empty white space, content concentrated in one
      small centered dialog box (<30% of image area)
    - Article: text spread vertically down the page (>50% of height has
      content)
    Measures the vertical spread of non-white pixels. If content covers
    less than 35% of the image height, it's a dialog/wall, not an article.
    """
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(path).convert("L")
        arr = np.array(im)
        # Non-white pixels (text, graphics, dialog boxes)
        content = arr < 200
        if not content.any():
            return True  # blank page
        rows_with_content = content.any(axis=1)
        top = rows_with_content.argmax()
        bottom = len(rows_with_content) - rows_with_content[::-1].argmax()
        spread = (bottom - top) / len(rows_with_content)
        # Also check: what fraction of pixels is content? Verification
        # pages are sparse (<5% content), articles are dense (>10%)
        density = content.mean()
        is_wall = spread < 0.35 and density < 0.08
        if is_wall:
            print(f"[visuals] verification page detected: "
                  f"spread={spread:.0%}, density={density:.1%}")
        return is_wall
    except Exception as e:
        print(f"[visuals] verification check failed: {e}")
        return False


def _is_adblock_wall(path: Path) -> bool:
    """Detect adblock/consent walls in screenshots (2026-10-11).

    Root-cause generalization of the verification-wall/paywall scans:
    access walls are a family. An adblock wall (e.g. TechCrunch's
    "Disable your adblocker" page) slips past both existing checks — its
    content spread is wide (footer text extends the range) and its CTA
    button is too small for the 45%-saturation paywall test.

    Signature: a SPARSE page (density < 6% — no article is this empty)
    dominated by one large SOLID vivid CTA button (the "disable adblock"
    / "accept" button). Legit sparse pages (e.g. a report landing page)
    have no such button; dense article pages never reach the button test.
    """
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(path).convert("RGB")
        arr = np.array(im).astype(float)
        gray = arr.mean(axis=2)
        density = (gray < 200).mean()
        if density >= 0.06:
            return False  # real article content — not a wall
        # Vivid pixels (saturated color = the CTA button, not gray text)
        sat = arr.max(axis=2) - arr.min(axis=2)
        vivid = sat > 80
        if vivid.mean() < 0.003:
            return False
        # Largest connected vivid component on a coarse grid
        small = np.array(Image.fromarray(vivid).resize(
            (160, 100), Image.NEAREST))
        seen = np.zeros_like(small, dtype=bool)
        total = small.size
        for y in range(small.shape[0]):
            for x in range(small.shape[1]):
                if small[y, x] and not seen[y, x]:
                    stack = [(y, x)]
                    seen[y, x] = True
                    xs, ys = [], []
                    while stack:
                        cy, cx = stack.pop()
                        ys.append(cy)
                        xs.append(cx)
                        for dy in (-1, 0, 1):
                            for dx in (-1, 0, 1):
                                ny, nx = cy + dy, cx + dx
                                if (0 <= ny < small.shape[0]
                                        and 0 <= nx < small.shape[1]
                                        and small[ny, nx] and not seen[ny, nx]):
                                    seen[ny, nx] = True
                                    stack.append((ny, nx))
                    n = len(xs)
                    box = ((max(ys) - min(ys) + 1)
                           * (max(xs) - min(xs) + 1))
                    fill = n / box if box else 0
                    # A solid vivid button: >1.5% of the image, rectangular
                    if n / total > 0.015 and fill > 0.8:
                        print(f"[visuals] adblock wall detected: sparse "
                              f"page (density={density:.1%}) with solid "
                              f"vivid button ({n/total:.1%} of image)")
                        return True
        return False
    except Exception as e:
        print(f"[visuals] adblock-wall check failed: {e}")
        return False


def _is_paywall_modal(path: Path) -> bool:
    """Detect paywall/email-gate modals in screenshots (2026-10-11).

    Paywalls show a centered solid-colored modal (teal/green/blue box)
    with an email input + button, blocking the article. Unlike verification
    pages (sparse), modals are DENSE solid blocks.
    Detects: high color saturation concentrated in the center region —
    articles are mostly white/gray text, modals are vivid solid colors.
    """
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(path).convert("RGB")
        arr = np.array(im).astype(float)
        h, w = arr.shape[:2]
        # Center region where modals appear
        cy1, cy2 = int(h * 0.30), int(h * 0.70)
        cx1, cx2 = int(w * 0.20), int(w * 0.80)
        center = arr[cy1:cy2, cx1:cx2]
        # Saturation = max(R,G,B) - min(R,G,B); high = vivid color
        sat = center.max(axis=2) - center.min(axis=2)
        saturated = (sat > 60).mean()
        # Paywall modals are vivid solid blocks: >45% saturated in center
        # Articles: text is gray/black, images are scattered (<35%)
        is_modal = saturated > 0.45
        if is_modal:
            print(f"[visuals] paywall modal detected: "
                  f"{saturated:.0%} saturated in center")
        return is_modal
    except Exception as e:
        print(f"[visuals] paywall check failed: {e}")
        return False


def microlink_screenshot(page_url: str):
    """Screenshot of a source article/post via Microlink.
    The documentary fallback: showing the actual source is always
    relevant and never a wrong visual. x.com pages get a narrow viewport
    so the screenshot is the post column, not the login sidebar."""
    # 2026-10-11: check page metadata for verification walls (root cause
    # fix — any site can serve a CAPTCHA, not just blacklisted domains).
    # Note: meta=true fails on some sites (e.g. barchart.com), so try
    # with meta first, fall back to without meta + pixel scan.
    VERIFICATION_KEYWORDS = (
        "verification required", "confirm you are human",
        "i am not a robot", "captcha", "prove you are human",
        "security check", "unusual activity",
    )
    try:
        params = {"url": page_url, "screenshot": "true",
                  "meta": "true", "waitForTimeout": 3000}
        if "x.com" in page_url or "twitter.com" in page_url:
            params["viewport.width"] = "900"
            params["viewport.height"] = "1400"
        else:
            # Mobile viewport for articles (2026-10-11): single-column
            # layout, no sidebars — the screenshot IS the content box.
            # Portrait aspect also matches the 9:16 video frame.
            params["viewport.width"] = "500"
            params["viewport.height"] = "900"
        r = requests.get("https://api.microlink.io", params=params,
                         timeout=90).json()
        if r.get("status") != "success":
            # meta=true failed — retry without meta (pixel scan is backup)
            params["meta"] = "false"
            r = requests.get("https://api.microlink.io", params=params,
                             timeout=90).json()
        if r.get("status") == "success":
            data = r.get("data") or {}
            # Check title/description for verification indicators
            title = (data.get("title") or "").lower()
            desc = (data.get("description") or "").lower()
            text = f"{title} {desc}"
            if any(kw in text for kw in VERIFICATION_KEYWORDS):
                print(f"[visuals] screenshot REJECTED (verification wall): "
                      f"'{page_url[:60]}' title='{title[:50]}'")
                return None
            return (data.get("screenshot") or {}).get("url")
    except Exception as e:
        print(f"[visuals] screenshot failed for '{page_url[:60]}': {e}")
    return None


def crop_x_screenshot(path: Path):
    """Crop an x.com screenshot to the post column, dropping the login
    sidebar / QR / 'relevant people' rail on the right."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cut = int(w * 0.63)
    im.crop((0, 0, cut, h)).save(path, quality=92)
    print(f"[visuals] x screenshot cropped {w}x{h} -> {cut}x{h}")


# ---------------------------------------------------------------------------
# Root-source resolution (user rule 2026-10-11 #2): aggregator/roundup/
# newsletter pages ("AI weekly", "top news") must never be shown. The
# pipeline follows through to the linked root article and screenshots that.
# ---------------------------------------------------------------------------
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag

_STOPWORDS = frozenset(
    "the a an and or of to in on for with by from at as is are was were be "
    "been has have had will would can could should this that these those it "
    "its vs via new top best daily weekly".split())


def _sig_tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(t) >= 4 and t not in _STOPWORDS}


class _PageScan(HTMLParser):
    """One pass over a page's HTML: og:type, JSON-LD article types, text
    inside <article>/known content containers, and outbound links."""

    _CONTENT_HINTS = ("article-body", "post-content", "entry-content",
                      "article-content", "story-content", "post-body",
                      "articleBody")

    def __init__(self):
        super().__init__()
        self.og_type = ""
        self.jsonld_article = False
        self._jsonld = False
        self._jsonld_buf = []
        self._depth = 0
        self._content_depth = -1
        self.content_chars = 0
        self.links = []
        self._a_href = None
        self._a_text = []
        self.h1_count = 0
        self.h2_count = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("property") == "og:type":
            self.og_type = a.get("content", "")
        if tag == "h1":
            self.h1_count += 1
        if tag == "h2":
            self.h2_count += 1
        if tag == "script" and a.get("type") == "ld+json":
            self._jsonld = True
            self._jsonld_buf = []
        self._depth += 1
        if tag == "article":
            self._content_depth = self._depth
        elif tag in ("div", "main", "section"):
            cls = f"{a.get('class', '')} {a.get('id', '')}".lower()
            if any(h in cls for h in self._CONTENT_HINTS):
                self._content_depth = self._depth
        if tag == "a" and a.get("href"):
            self._a_href = a["href"]
            self._a_text = []

    def handle_endtag(self, tag):
        if tag == "script" and self._jsonld:
            self._jsonld = False
            blob = "".join(self._jsonld_buf)
            if re.search(r'"@type"\s*:\s*"(NewsArticle|BlogPosting|Article)"',
                         blob):
                self.jsonld_article = True
        if self._content_depth == self._depth:
            self._content_depth = -1
        self._depth = max(0, self._depth - 1)
        if tag == "a" and self._a_href is not None:
            txt = " ".join("".join(self._a_text).split())
            if len(txt) >= 25:
                self.links.append((self._a_href, txt))
            self._a_href = None

    def handle_data(self, data):
        if self._jsonld:
            self._jsonld_buf.append(data)
        if self._content_depth != -1:
            self.content_chars += len(data.strip())
        if self._a_href is not None:
            self._a_text.append(data)


def _find_credited_source(html, page_url):
    """If the page republishes another outlet's story, return the credited
    root article URL. Looks for source attribution (e.g. 'source':
    'venturebeat.com') paired with an outbound article link to that domain.
    Returns None when no credited external source is found.

    Strategic log: prints the credited domain and chosen URL, or why not.
    """
    tag = f"[resolve] {page_url[:50]}"
    # Find credited domains: JSON-LD/text attribution like
    # 'source">venturebeat.com' or 'via venturebeat'.
    credited = set()
    for m in re.finditer(
            r'(?:source|via|courtesy|originally)[">:\s]*([a-z0-9-]+\.[a-z]{2,})',
            html[:100000], re.I):
        d = m.group(1).lower()
        if d not in urldefrag(page_url).url.lower():
            credited.add(d)
    if not credited:
        print(f"{tag}: no credited external source")
        return None
    print(f"{tag}: credited domain(s): {sorted(credited)}")
    # Find the best outbound article link to a credited domain.
    page_norm = urldefrag(page_url).url
    best = None
    for m in re.finditer(r'href=["\'](https?://[^"\']+)["\']', html, re.I):
        abs_url = urldefrag(m.group(1)).url
        if abs_url == page_norm or not abs_url.startswith("http"):
            continue
        dom = re.sub(r"^www\.", "", abs_url.split("/")[2].lower())
        if any(dom == c or dom.endswith("." + c) for c in credited):
            # Prefer article-like URLs (dated or long slug).
            score = (2 if re.search(r"/\d{4}/\d{1,2}/", abs_url) else 0
                     + (1 if len(abs_url.split("/")[-1]) > 20 else 0))
            if best is None or score > best[1]:
                best = (abs_url, score)
    if best:
        print(f"{tag}: root source -> {best[0][:80]}")
        return best[0]
    print(f"{tag}: credited but no article link found")
    return None


def _resolve_root_source(page_url, title_hint="", subject_hint=""):
    """Return the URL to screenshot for page_url.

    - Root article/post pages return unchanged.
    - Aggregator/roundup/newsletter pages resolve to the linked article
      best matching the story; unresolvable ones return None (the page
      must not be shown — user rule 2026-10-11).
    Conservative: ambiguous pages screenshot as-is; only confident
    aggregators (no article signals + many content links) divert.
    """
    try:
        r = requests.get(page_url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"},
            timeout=20)
        html = r.text
        if len(html) < 2000:
            return page_url
    except Exception as e:
        print(f"[visuals] root-source scan failed for '{page_url[:60]}': "
              f"{e} — screenshotting as-is")
        return page_url
    try:
        scan = _PageScan()
        scan.feed(html)
    except Exception:
        return page_url
    # Article signals: it's a single story page (not a listing).
    # - Dated URL paths (/2026/10/08/slug) are articles, not roundups
    #   (2026-10-11: TechCrunch uses no og:type/<article>/JSON-LD).
    # - Single-h1 heading structure = one story, not a listing.
    is_article = (
        re.search(r"/\d{4}/\d{1,2}/\d{1,2}/", page_url)
        or scan.og_type.lower() == "article"
        or scan.jsonld_article
        or scan.content_chars > 800
        or (scan.h1_count == 1 and scan.h2_count < 15))
    if is_article:
        # Republication check (2026-10-11): even a valid article page may
        # be republishing someone else's story (e.g. aiweekly.co crediting
        # venturebeat.com). If the page links to an external article from
        # a credited source, follow it to the root.
        root = _find_credited_source(html, page_url)
        if root and root != page_url:
            print(f"[resolve] '{page_url[:60]}' republishes from "
                  f"'{root[:70]}' -> using root source")
            return root
        return page_url
    # Confident aggregator? Many content links, no article body.
    if len(scan.links) < 15:
        return page_url
    hint_tokens = _sig_tokens(f"{title_hint} {subject_hint}")
    if not hint_tokens:
        return page_url
    page_norm = urldefrag(page_url).url
    best, best_score = None, 0
    for href, txt in scan.links:
        abs_url = urldefrag(urljoin(page_url, href)).url
        if not abs_url.startswith("http") or abs_url == page_norm:
            continue
        score = len(_sig_tokens(txt) & hint_tokens)
        if score > best_score:
            best, best_score = abs_url, score
    if best and best_score >= 2:
        print(f"[visuals] aggregator '{page_url[:60]}' -> root source "
              f"'{best[:70]}'")
        return best
    print(f"[visuals] aggregator page '{page_url[:60]}' — root source not "
          f"resolvable, skipping (never show roundup pages)")
    return None


def _crop_to_content(dest):
    """Crop a page screenshot to its article content (user rule 2026-10-11 #1).

    Two paths:
    - Portrait/mobile screenshots: single-column layout. Find the headline
      (largest text in the top half) and crop from just above it, dropping
      the site header/subscribe chrome above and promos below.
    - Landscape/desktop screenshots: band-pass text-density crop (legacy).

    Strategic log: every decision is printed with the [crop] tag for
    pipeline tracing.
    """
    import cv2
    tag = f"[crop] {Path(dest).name[:40]}"
    try:
        img = cv2.imread(str(dest))
        if img is None:
            print(f"{tag}: cannot read image")
            return False
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if float(gray.mean()) > 110:
            _, mask = cv2.threshold(gray, 110, 255, cv2.THRESH_BINARY_INV)
            pol = "dark-on-light"
        else:
            _, mask = cv2.threshold(gray, 145, 255, cv2.THRESH_BINARY)
            pol = "light-on-dark"

        if h > w:
            # PORTRAIT (mobile): headline-anchored crop.
            # Merge glyphs into lines first (horizontal close), then the
            # headline is the tallest TEXT LINE below the site header.
            kx = max(30, w // 20)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kx, 7))
            lines = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            n, labels, stats, _ = cv2.connectedComponentsWithStats(lines, 8)
            headline_y, headline_h = None, 0
            for i in range(1, n):
                bh = stats[i, cv2.CC_STAT_HEIGHT]
                by = stats[i, cv2.CC_STAT_TOP]
                bw = stats[i, cv2.CC_STAT_WIDTH]
                # Headline line: tall (>24px), wide (>30% width), below
                # the site header (y>120), in the top 50%. TOPMOST wins
                # (article headline sits above hero images/logos).
                if bh > 16 and bw > w * 0.25 and 120 < by < 450:
                    if headline_y is None or by < headline_y:
                        headline_y, headline_h = by, bh
            if headline_y is None:
                # Fallback: content-based density scan (2026-10-11). Fixed
                # y-zones misfire when blank ad slots shift the headline
                # (notebookcheck: 450px blank pushed headline to y=600).
                # Scan from below the header: skip zero-density blank
                # regions, land on the first sustained text-dense band.
                row_den = (mask > 0).mean(axis=1)
                y0, y1 = 300, 900  # ultimate fallback
                run = 0
                for y in range(150, h):
                    if row_den[y] > 0.03:
                        run += 1
                        if run >= 25:
                            y0 = max(0, y - 25 - 20)
                            y1 = min(h, y0 + 600)
                            print(f"{tag}: {pol}, density scan found "
                                  f"content at y={y - 25}")
                            break
                    else:
                        run = 0
            else:
                y0 = max(0, headline_y - 30)
                y1 = min(h, y0 + 560)
                print(f"{tag}: {pol}, portrait {w}x{h}, headline at y={headline_y}")
        else:
            # LANDSCAPE (desktop): band-pass density crop.
            row_den = (mask > 0).mean(axis=1)
            def _is_text(d):
                return 0.03 < d < 0.6
            y0, y1 = 0, h
            run = 0
            for y in range(h):
                if _is_text(row_den[y]):
                    run += 1
                    if run >= 30 and y0 == 0:
                        y0 = y - 30
                        break
                else:
                    run = 0
            run = 0
            for y in range(h - 1, -1, -1):
                if _is_text(row_den[y]):
                    run += 1
                    if run >= 30:
                        y1 = y + 30
                        break
                else:
                    run = 0
            y0, y1 = max(0, y0), min(h, y1)
            print(f"{tag}: {pol}, landscape {w}x{h}, rows {y0}-{y1}")
            if y1 - y0 < 0.25 * h:
                print(f"{tag}: band too short - keeping full")
                return False

        # Horizontal: for portrait, keep full width (single column).
        # For landscape, find the widest text-dense band.
        if h > w:
            x0, x1 = 0, w
        else:
            col_den = (mask[y0:y1] > 0).mean(axis=0)
            best, cur_s = None, -1
            for x in range(w):
                if 0.03 < col_den[x] < 0.6:
                    if cur_s < 0:
                        cur_s = x
                else:
                    if cur_s >= 0:
                        width = x - cur_s
                        if width > w * 0.15 and (best is None or width > best[1] - best[0]):
                            best = (cur_s, x)
                        cur_s = -1
            if cur_s >= 0:
                width = w - cur_s
                if width > w * 0.15 and (best is None or width > best[1] - best[0]):
                    best = (cur_s, w)
            if not best:
                print(f"{tag}: no text column - keeping full")
                return False
            x0, x1 = best

        pad = 20
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1, y1 = min(w, x1 + pad), min(h, y1 + pad)
        if (x1 - x0) * (y1 - y0) < 0.08 * w * h:
            print(f"{tag}: box too small - keeping full")
            return False
        Image.open(dest).convert("RGB").crop((x0, y0, x1, y1)).save(
            dest, quality=92)
        print(f"{tag}: CROPPED {w}x{h} -> {x1 - x0}x{y1 - y0}")
        return True
    except Exception as e:
        print(f"{tag}: crop failed ({e}) - keeping full")
        return False


def _screenshot_article(page_url, title_hint="", subject_hint=""):
    """Guaranteed documentary fallback (user rule 2026-10-11 #3): resolve
    aggregator pages to their root article (#2), screenshot it, reject
    walls/modals, and crop to the text content box (#1).

    Returns (dest_path, shown_url) or (None, None) when no usable
    screenshot could be produced.
    """
    tag = f"[shot] {page_url[:55]}"
    print(f"{tag}: ANALYZE -> resolve root source")
    rurl = _resolve_root_source(page_url, title_hint, subject_hint)
    if rurl is None:
        print(f"{tag}: SKIP - unresolvable aggregator, no root found")
        return None, None
    if rurl != page_url:
        print(f"{tag}: RESOLVED -> {rurl[:70]}")
    else:
        print(f"{tag}: root confirmed (already an article)")
    surl = microlink_screenshot(rurl)
    if not surl:
        print(f"{tag}: FAIL - microlink screenshot failed")
        return None, None
    dest = CACHE / f"screenshot_{slug(rurl)}.jpg"
    try:
        download(surl, dest)
    except Exception as e:
        print(f"{tag}: FAIL - download failed: {e}")
        return None, None
    if dest.stat().st_size <= 10_000:
        print(f"{tag}: FAIL - screenshot too small "
              f"({dest.stat().st_size}b)")
        dest.unlink(missing_ok=True)
        return None, None
    if (_is_verification_page(dest) or _is_paywall_modal(dest)
            or _is_adblock_wall(dest)):
        print(f"{tag}: REJECTED - wall/modal detected")
        dest.unlink(missing_ok=True)
        return None, None
    print(f"{tag}: VALID screenshot, cropping to content")
    if "x.com" in rurl or "twitter.com" in rurl:
        crop_x_screenshot(dest)
    else:
        _crop_to_content(dest)
    print(f"{tag}: DONE -> {dest.name}")
    return dest, rurl


def norm_w(w: str) -> str:
    return re.sub(r"[^a-z0-9]", "", w.lower())


def match_shot(shot_text: str, seg_words, seg_start: float, seg_end: float,
               start_idx: int = 0):
    """(start, end, end_idx) timestamps for a shot by matching its words
    against the word stream. Falls back to None.

    start_idx: only consider matches at/after this word index — shots are
    matched SEQUENTIALLY, so a shot whose opening word repeats an earlier
    shot's ("Google ... Google says ...") can't steal the earlier shot's
    timing. Without this, duplicate openers collapse two shots onto the
    same start and the segment's visual timing corrupts.
    """
    want = [norm_w(w) for w in shot_text.split()]
    want = [w for w in want if w]
    if not want or not seg_words:
        return None
    have = [norm_w(w["word"]) for w in seg_words]
    # Find the want sequence as an ordered subsequence of have, at/after
    # start_idx. Prefer the TIGHTEST span (closest to a verbatim run).
    best = None
    for s in range(start_idx, len(have)):
        if have[s] != want[0]:
            continue
        h, wi = s, 0
        while h < len(have) and wi < len(want):
            if have[h] == want[wi]:
                wi += 1
            h += 1
        if wi == len(want):
            cand = (seg_words[s]["start"], seg_words[h - 1]["end"], h)
            if best is None or (cand[1] - cand[0]) < (best[1] - best[0]):
                best = cand
    return best


def fetch_visual(spec: dict, dur: float, w: int, h: int, script_title: str,
                 idx: int, page_urls: list = None, prev_path: str = None,
                 used_shot_urls: set = None, story_title: str = ""):
    """Resolve one visual per the evidence/illustrative tier. Returns
    (kind, path, source, shot_url). Source is explicit — a wrong or generic visual
    is a hallucination vector, so fallbacks are labeled, never silent.
    shot_url is the page URL when the visual is a screenshot, else None.

    NO-REPEAT RULE (user, 2026-10-11): the same article must never appear
    twice in one video, not even cropped differently. page_urls already
    shown by another shot (tracked in used_shot_urls) are skipped, never
    re-screenshotted with a different crop.

    Sourcing policy (user, 2026-10-08): the agent research loop searches
    and verifies relevance, pinning verified files into the cache. The
    pipeline itself NEVER queries Commons or stock for evidence shots —
    blind search results hallucinate (log cabin for "Lean", machinery for
    "X Lift", wrong monuments). Stock is reserved for notable generic
    actions (the illustrative tier) only.
    """
    vtype = spec.get("visual_type", "illustrative")
    q = spec.get("broll") or "technology abstract"
    banned = _banned_slugs()
    retry = _retry_mode()
    off = 1 if retry else 0  # quarantine retry: take the 2nd search hit
    clip_dest = CACHE / f"{slug(q)}.mp4"
    photo_dest = CACHE / f"{slug(q)}.jpg"
    kind, path, source, shot_url = None, None, None, None
    # Verified pins first (agent-searched, relevance-checked).
    # 2026-10-12: accept .png pins too — the pin convention is .jpg/.mp4
    # but a .png pin is still a verified pin; never skip one on extension.
    for cand in (VCACHE / f"{slug(q)}.mp4", VCACHE / f"{slug(q)}.jpg",
                 VCACHE / f"{slug(q)}.png"):
        if cand.exists() and cand.stat().st_size >= 10_000:
            kind = "clip" if cand.suffix == ".mp4" else "photo"
            path = str(cand)
            source = "verified-pin"
            break
    # Legacy cache: blind stock downloads are reusable ONLY for the
    # illustrative tier (stock's reserved purpose). Evidence shots must
    # be verified pins — never legacy blind downloads. Banned slugs
    # (quarantine retry) are skipped so the retry shows different clips.
    if path is None and vtype == "illustrative" and slug(q) not in banned:
        for cand in (clip_dest, photo_dest):
            if cand.exists() and cand.stat().st_size >= 10_000:
                kind = "clip" if cand.suffix == ".mp4" else "photo"
                path = str(cand)
                source = "cache"
                break
    # Semantic clip library: a proven clip for a similar past query beats
    # a fresh blind search. Illustrative tier only.
    if path is None and vtype == "illustrative":
        lib = library_match(q, prev_path=prev_path)
        if lib:
            kind, path = lib
            source = "clip-library"
    # Evidence tier: the visual IS the thing (person, logo, landmark,
    # product, document). Only agent-verified cache pins or the story's
    # own media qualify — no Commons, no stock. Anything unpinned falls
    # through to screenshot -> title card, never a blind guess.
    is_person = bool(spec.get("person"))
    if path is None and is_person:
        # Named people: never stock, never blind search. A missing visual
        # is honest, a wrong one is a hallucination.
        print(f"[visuals] shot {idx}: NO_FIND person "
              f"'{spec.get('visual_subject')}' — screenshot/title, not stock")
    if path is None and vtype == "illustrative":
        # Stock is reserved for notable generic actions. Bounded relevance
        # loop: specific video -> specific photo -> broadened query.
        queries = [q, " ".join(q.split()[:2])]
        for qq in queries:
            for mkind, mdest in (("videos", clip_dest),
                                 ("photos", photo_dest)):
                if path:
                    break
                try:
                    url = pixabay_media(qq, mkind, offset=off)
                except Exception as e:
                    print(f"[visuals] pixabay {mkind} failed for '{qq}': {e}")
                    url = None
                provider = None
                if not url and mkind == "videos":
                    try:
                        url = pexels_search(qq, offset=off)
                        provider = "pexels" if url else None
                    except Exception as e:
                        print(f"[visuals] pexels failed for '{qq}': {e}")
                if not provider and url:
                    provider = "pixabay"
                if url:
                    try:
                        download(url, mdest)
                        kind = "clip" if mkind == "videos" else "photo"
                        path = str(mdest)
                        source = provider or mkind
                        print(f"[visuals] shot {idx}: '{qq}' -> {kind} [{source}]")
                        # Remember it: the clip library reuses proven
                        # footage for similar future queries.
                        library_register(qq, kind, mdest)
                        if kind == "clip":
                            # Blind stock is a hallucination vector (a night-
                            # earth clip once illustrated "AI generated
                            # images"). Save a 3-frame strip so the frame
                            # review can eyeball the clip, not just one frame.
                            clip_review_strip(mdest, idx)
                    except Exception as e:
                        print(f"[visuals] download failed for '{qq}': {e}")
                        mdest.unlink(missing_ok=True)
    if path is None:
        # Documentary fallback (user rule 2026-10-11 #3): the cropped
        # root-source article screenshot is the GUARANTEED fallback when
        # no better visual (verified pin, story media, stock) was found.
        # _screenshot_article resolves aggregator pages to the root
        # article (#2) and crops to the text content box (#1).
        # On a quarantine retry the first URL already failed QA, so start
        # from the next one.
        urls = page_urls or []
        if _retry_mode() and len(urls) > 1:
            urls = urls[1:] + urls[:1]
        for purl in urls:
            if path:
                break
            # NO-REPEAT (2026-10-11): this page is already on screen in
            # another shot — showing it again, even cropped, is a repeat.
            # Skip to the next URL; never manufacture a variant crop.
            if used_shot_urls is not None and purl in used_shot_urls:
                print(f"[visuals] shot {idx}: page already shown in this "
                      f"video — skipping '{purl[:60]}'")
                continue
            dest, rurl = _screenshot_article(
                purl, story_title, spec.get("visual_subject") or "")
            if dest is None:
                continue
            if used_shot_urls is not None and rurl in used_shot_urls:
                print(f"[visuals] shot {idx}: resolved root source already "
                      f"shown — skipping '{rurl[:60]}'")
                continue
            kind, path, source = "photo", str(dest), "screenshot"
            shot_url = rurl
            print(f"[visuals] shot {idx}: screenshot '{rurl[:60]}' -> photo")
    if path is None:
        # 2026-10-10: NO title-card fallback (user). If no pin and no
        # screenshot worked, fail loudly so a human pins a visual.
        # (The caller applies story-logo fallback after this returns.)
        print(f"[visuals] shot {idx}: ERROR — no visual available for "
              f"'{q[:60]}'. Pin a verified photo or fix the source URL. "
              f"Title cards are disabled.")
        # Use black frame (narration + captions only) rather than a
        # misleading title card
        from PIL import Image
        black_path = ROOT / "output" / f"black_{idx:02d}.png"
        Image.new("RGB", (w, h), (0, 0, 0)).save(black_path)
        path = str(black_path)
        kind, source = "photo", "black-frame"
    # Evidence shots must never come from blind search — if one did, the
    # sourcing policy was bypassed. Flag it loudly instead of passing
    # silently.
    if vtype == "evidence" and source in ("pixabay", "photos", "videos",
                                          "pexels"):
        print(f"[visuals] shot {idx}: POLICY VIOLATION — blind {source} "
              f"used for evidence '{spec.get('visual_subject')}'")
    return kind, path, source, shot_url


def main():
    import sys
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    script = json.loads((ROOT / "output" / "script.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    words = json.loads((ROOT / "output" / "words.json").read_text())
    w, h = CFG[mode]["width"], CFG[mode]["height"]

    visuals = []

    # NO-REPEAT (2026-10-11): page URLs already screenshotted for another
    # shot this run — fetch_visual skips them so the same article never
    # appears twice, even cropped.
    used_shot_urls = set()

    # Quarantine retry: delete banned stock files so the re-fetch can't
    # silently reuse the clips QA rejected.
    for bs in _banned_slugs():
        for cand in (CACHE / f"{bs}.mp4", CACHE / f"{bs}.jpg"):
            if cand.exists():
                cand.unlink()
                print(f"[visuals] retry: banned clip removed ({cand.name})")

    # Pre-pass per story, in relevance order:
    #   1. the publisher's own page media (og:video / og:image) — editorially
    #      chosen for the story, the most reliable match.
    #   2. the story's own X post video (x_media_url, or x.com story URL) —
    #      primary source when the story broke on X.
    # Later shots fall through to the evidence/illustrative loop below.
    story_assets = {}  # sid -> [(kind, local_path), ...]
    for sid, src in zip(script.get("story_ids", []),
                        script.get("sources", [])):
        if not sid:
            continue
        assets = []
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
        if assets:
            story_assets[sid] = assets

    # Words per segment, from absolute whisper timestamps + tts timings.
    seg_word_ranges = []
    for i, tm in enumerate(timings):
        s, e = tm["start"], tm["start"] + tm["duration"] + CFG["tts"]["segment_gap_sec"]
        seg_word_ranges.append(
            [ww for ww in words if ww["start"] >= s - 0.05 and ww["start"] < e])

    story_asset_n = {}
    # story_id -> [article_url, x_media_url] for the screenshot fallback.
    sid_to_urls = {}
    sid_to_title = {}
    for sid, src in zip(script.get("story_ids", []),
                        script.get("sources", [])):
        if sid:
            # x_media_url may be a single URL or a list of them.
            xm = src.get("x_media_url")
            xm_list = xm if isinstance(xm, list) else ([xm] if xm else [])
            sid_to_urls[sid] = [u for u in [src.get("url")] + xm_list if u]
            sid_to_title[sid] = src.get("title") or ""
    def _subject_spoken_at(visual_subject, seg_words, s_time, e_time):
        """First time visual_subject is spoken within [s_time, e_time].

        Returns the word's start time, or None. Multi-word subjects
        ("White House") match consecutive words. Used for evidence-sync:
        don't show a subject's visual before the subject is named."""
        if not visual_subject:
            return None
        subj = re.sub(r"[^a-z0-9 ]", "", str(visual_subject).lower()).split()
        if not subj:
            return None
        wr = [w for w in seg_words
              if s_time - 0.05 <= w["start"] < e_time]
        norm = lambda s_: re.sub(r"[^a-z0-9]", "", s_.lower())
        for k in range(len(wr) - len(subj) + 1):
            if all(norm(wr[k + m]["word"]) == subj[m]
                   for m in range(len(subj))):
                return wr[k]["start"]
        return None

    for i, seg in enumerate(script["segments"]):
        sid = seg.get("story_id")
        seg_kind = seg.get("kind", "story")  # hook | headlines | story
        tm = timings[i]
        seg_start = tm["start"]
        seg_words = seg_word_ranges[i] if i < len(seg_word_ranges) else []
        shots = seg.get("shots") or [dict(seg, text=seg["text"])]
        # Shot time ranges via word matching (sequential: each shot
        # matches at/after the previous shot's end); fallback = even split.
        ranges = []
        ok = True
        search_from = 0
        for sh in shots:
            m = match_shot(sh.get("text", ""), seg_words, seg_start,
                           tm["start"] + tm["duration"], start_idx=search_from)
            if m is None:
                ok = False
                break
            ranges.append((m[0], m[1]))
            search_from = m[2]
        if not ok or not ranges:
            n = len(shots)
            total = tm["duration"] + CFG["tts"]["segment_gap_sec"]
            ranges = [(seg_start + total * k / n, seg_start + total * (k + 1) / n)
                      for k in range(n)]
        # Last shot fills to the segment end (+ inter-segment gap) so shots
        # sum to the narration length.
        seg_total = tm["duration"] + CFG["tts"]["segment_gap_sec"]
        ranges[-1] = (ranges[-1][0], seg_start + seg_total)
        for j, sh in enumerate(shots):
            s_time, e_time = ranges[j]
            # Evidence-sync (2026-10-09): an evidence shot must not show its
            # subject before the subject is named. If the visual_subject is
            # first spoken mid-range (e.g. shot starts "the federal AI..."
            # but shows the Nvidia building 3.7s before "Nvidia" is said),
            # start the shot when the subject is spoken — the previous shot
            # extends to cover the gap (render.py stretches shots to the
            # next shot's start).
            subj_at = _subject_spoken_at(sh.get("visual_subject"),
                                         seg_words, s_time, e_time)
            if (subj_at is not None
                    and sh.get("visual_type") == "evidence"
                    and subj_at > s_time + 0.4
                    and subj_at < e_time - 1.0):
                print(f"[visuals] shot {idx}: evidence-sync "
                      f"{s_time:.2f}->{subj_at:.2f}s "
                      f"('{sh.get('visual_subject')}' spoken)")
                s_time = subj_at
            dur = max(0.8, e_time - s_time)
            idx = len(visuals)
            # First shot of a story segment consumes the story's next owned
            # asset (publisher/X media) — unless the shot names a person.
            # A person shot must show the person; the publisher image is
            # often about a secondary subject. Hook segments use their own
            # shot spec for the same reason.
            # Agent-verified pins outrank story-owned: if the research loop
            # pinned a verified file for this shot's query, use it.
            # Verified pins live in cache/verified/ — legacy blind
            # downloads in cache/ never count as verified.
            q = sh.get("broll") or "technology abstract"
            pinned = None
            for cand in (VCACHE / f"{slug(q)}.mp4", VCACHE / f"{slug(q)}.jpg"):
                if cand.exists() and cand.stat().st_size >= 10_000:
                    if cand.suffix == ".jpg" and _is_text_card(str(cand)):
                        print(f"[visuals] shot {idx}: REJECTED text-card pin "
                              f"{cand.name} — not a photo")
                        continue
                    pinned = ("clip" if cand.suffix == ".mp4" else "photo",
                              str(cand))
                    break
            n = story_asset_n.get(sid, 0)
            assets = story_assets.get(sid, []) if sid else []
            shot_url = None  # only screenshots record a page URL
            if pinned:
                kind, path = pinned
                source = "verified-pin"
                print(f"[visuals] shot {idx}: verified pin -> {kind}")
            elif (j == 0 and n < len(assets) and seg_kind == "story"
                    and not sh.get("person")):
                story_asset_n[sid] = n + 1
                kind, path = assets[n]
                source = "story-owned"
                print(f"[visuals] shot {idx}: story-owned {kind} -> {kind}")
            else:
                page_urls = sid_to_urls.get(sid, [])
                prev_path = visuals[-1]["path"] if visuals else None
                kind, path, source, shot_url = fetch_visual(sh, dur, w, h,
                                                 script["title"], idx,
                                                 page_urls, prev_path,
                                                 used_shot_urls,
                                                 sid_to_title.get(sid, ""))
            # NO-LOGO-FULLSHOT (user, 2026-10-11): company logos must never
            # fill the frame during story deep-dives. The old logo-fallback
            # (story-opening shot -> story_icons logo) is deleted; the shot
            # keeps whatever visual fetch_visual resolved.
            if (seg_kind == "story" and Path(path).name.startswith("logo_")):
                print(f"[visuals] WARNING shot {idx}: logo file "
                      f"{Path(path).name} would fill the frame in a story "
                      f"deep-dive — pin a photo/building/person instead")
            entry = {"idx": idx, "segment": i, "kind": kind,
                     "path": path, "duration": round(dur, 3),
                     "seg_kind": seg_kind, "start": round(s_time, 3),
                     "source": source,
                     "shot_url": shot_url,  # page URL if a screenshot
                     "person": bool(sh.get("person")),
                     # Document-ish shots (articles, docs, tables, posts):
                     # dense text must not be cropped by an aggressive
                     # Ken Burns punch-in at render.
                     "doc": kind == "photo" and any(
                         k in (sh.get("broll") or "").lower()
                         for k in ("article", "page", "website", "screenshot",
                                   "document", "table", "chart", "post",
                                   "announcement", "blog", "detector",
                                   "interface", "pricing"))}
            if entry["person"] and kind == "photo":
                entry["face_xy"] = detect_face(path)
                if entry["face_xy"]:
                    print(f"[visuals] shot {idx}: face at {entry['face_xy']}")
            # Logo overlay RETIRED 2026-10-09 (shot-grammar rule 12): the
            # top-right corner now carries the story number badge, rendered
            # by render.py. Company marks appear only as shot subjects.
            # logo_overlay in old scripts is ignored.
            if sh.get("logo_overlay"):
                print(f"[visuals] shot {idx}: logo_overlay retired — "
                      f"corner now shows the story number")
            if entry.get("shot_url"):
                used_shot_urls.add(entry["shot_url"])
            visuals.append(entry)
    # Speech-aligned cuts (2026-10-08): a new segment's visual must land
    # exactly when its narration starts, not ~0.5s earlier inside the
    # inter-segment pause (viewers read that as "the narrator is late").
    # Move the pause onto the previous shot's tail: shift the boundary
    # forward to the segment's first word, keeping total duration identical
    # so A/V sync can't drift.
    first_word_start = {}
    for i in range(len(timings)):
        sw = seg_word_ranges[i] if i < len(seg_word_ranges) else []
        if sw:
            first_word_start[i] = sw[0]["start"]
    for k in range(1, len(visuals)):
        if visuals[k]["segment"] == visuals[k - 1]["segment"]:
            continue
        fw = first_word_start.get(visuals[k]["segment"])
        if not fw:
            continue
        # Case 1 (2026-10-08): shot starts too EARLY (in the pause) — shift
        # the boundary forward to the first word.
        if fw > visuals[k]["start"] + 0.05:
            shift = round(fw - visuals[k]["start"], 3)
            if visuals[k]["duration"] - shift >= 0.8:
                visuals[k - 1]["duration"] = round(
                    visuals[k - 1]["duration"] + shift, 3)
                visuals[k]["start"] = round(fw, 3)
                visuals[k]["duration"] = round(
                    visuals[k]["duration"] - shift, 3)
                print(f"[visuals] shot {visuals[k]['idx']}: cut aligned to "
                      f"speech (+{shift:.2f}s)")
        # Case 2 (2026-10-10): shot starts too LATE (previous shot bleeds
        # into the new segment's narration) — pull the boundary back to the
        # first word so the visual changes exactly when narration starts.
        elif visuals[k]["start"] > fw + 0.05:
            shift = round(visuals[k]["start"] - fw, 3)
            if visuals[k - 1]["duration"] - shift >= 0.8:
                visuals[k - 1]["duration"] = round(
                    visuals[k - 1]["duration"] - shift, 3)
                visuals[k]["start"] = round(fw, 3)
                visuals[k]["duration"] = round(
                    visuals[k]["duration"] + shift, 3)
                print(f"[visuals] shot {visuals[k]['idx']}: cut aligned to "
                      f"speech (-{shift:.2f}s)")
    # A/V sync (2026-10-09): the visual timeline must equal the narration
    # timeline. Shot durations used to span only [first_word, last_word],
    # silently dropping every inter-shot pause from the video — the visuals
    # ran ~4.5s ahead by the end ("shots transition before the texts
    # finish") and the tail froze on a cloned frame. Extend each shot to
    # the next shot's start so the pause belongs to the outgoing shot;
    # cuts then land exactly when the next narration begins. (The last
    # shot already fills to the narration end.)
    for k in range(len(visuals) - 1):
        visuals[k]["duration"] = round(
            visuals[k + 1]["start"] - visuals[k]["start"], 3)
    # Duplicate-image guard (2026-10-11, user: "how do we prevent bad images").
    # The same stock infographic shipped on two different stories because a
    # generic aggregator URL served its og:image for the Anthropic story.
    # If two shots resolve to byte-identical images, the later one is wrong —
    # replace it with a screenshot of its own story's source.
    _dedupe_shot_images(visuals, script)
    # Headline-hook pairs (2026-10-11): the 5 numbered story hooks
    # (00:05-00:34) show the stacked person-photo + company-logo pair,
    # not the generic visual. Auto-built here from the pinned person
    # photos + story_icons logos so the daily run never needs manual work.
    _build_hook_pairs(script, mode)
    for s in visuals:
        if s.get("seg_kind") == "hook" and s.get("segment") not in (0, None):
            seg_idx = s["segment"]
            if seg_idx < len(script.get("segments", [])):
                sid = script["segments"][seg_idx].get("story_id")
                if sid:
                    _sfx = "_landscape" if mode == "landscape" else ""
                    pair = (ROOT / "cache" / "verified"
                            / f"hook_pair_{sid}{_sfx}.png")
                    if pair.exists():
                        s["path"] = str(pair.resolve())
                        s["kind"] = "photo"
                        print(f"[visuals] hook {seg_idx}: pair {pair.name}")
                    else:
                        print(f"[visuals] WARNING: hook pair missing for {sid}")
    (ROOT / "output" / "visuals.json").write_text(json.dumps(visuals, indent=2))
    print(f"[visuals] {len(visuals)} shots planned")


def _dhash(path, n=16):
    """Difference hash of a still image -> 256-bit int. Catches crops,
    resizes and recompressions of the same image that SHA-256 misses.
    Returns None when the image can't be read."""
    try:
        from PIL import Image
        im = Image.open(path).convert("L").resize((n + 1, n), Image.LANCZOS)
        px = im.load()
        h = 0
        for y in range(n):
            for x in range(n):
                h = (h << 1) | (1 if px[x, y] < px[x + 1, y] else 0)
        return h
    except Exception:
        return None


def _ham(a, b):
    return bin(a ^ b).count("1")


DHASH_MAX_DIST = 12  # of 256 bits: same image, cropped/resized/recompressed


def _dedupe_shot_images(visuals, script):
    """Every shot must show its own visual — the same article/image must
    never appear twice in one video, not even cropped differently.

    2026-10-11 root-cause fix: two code paths used to MANUFACTURE the
    repeats this guard was supposed to prevent — fetch_visual and the
    old dedupe both cropped a different 65% band of the same screenshot
    "so consecutive shots never match" the byte check. The user sees the
    same article twice. Both variant-crop paths are deleted. Detection is
    now three-layered:
      1. byte-identical files (SHA-256),
      2. screenshots from the same page URL (a crop is still the article),
      3. perceptual near-duplicates (dHash Hamming <= 12: crops, resizes,
         recompressions from different URLs).
    Verified pins are deliberate worker choices and are never replaced;
    only blind sources (screenshots, story-owned, stock) get replaced.
    A replacement never reuses a page URL already on screen — it tries the
    story's other source URLs, and if none are fresh the shot is flagged
    duplicate-needs-review instead of shipping a cropped repeat.
    """
    import hashlib
    # Per-story source URLs (primary + x_media_url) and titles, for
    # replacements and root-source resolution.
    story_url_lists = {}
    story_titles = {}
    for sid, src in zip(script.get("story_ids", []), script.get("sources", [])):
        if sid:
            xm = src.get("x_media_url")
            xm_list = xm if isinstance(xm, list) else ([xm] if xm else [])
            story_url_lists[sid] = [u for u in [src.get("url")] + xm_list if u]
            story_titles[sid] = src.get("title") or ""
    # Map flat shot idx -> story id for replacements
    idx_to_sid = {}
    flat_idx = 0
    for seg in script.get("segments", []):
        sid = seg.get("story_id")
        for _ in seg.get("shots", []):
            idx_to_sid[flat_idx] = sid
            flat_idx += 1

    def _replace_with_fresh_screenshot(v, used_urls, seen_exact, seen_ph):
        """Screenshot the story's first not-yet-shown source URL: resolve
        aggregators to the root article, reject walls, crop to the text
        content box. Returns True on success, False when every URL is used
        or failed."""
        sid = idx_to_sid.get(v["idx"])
        title_hint = story_titles.get(sid, "")
        for url in story_url_lists.get(sid, []):
            if url in used_urls:
                continue
            dest, rurl = _screenshot_article(url, title_hint, "")
            if dest is None:
                continue
            if rurl in used_urls:
                continue  # resolved root already on screen
            h2 = hashlib.sha256(open(dest, "rb").read()).hexdigest()
            if h2 in seen_exact:
                continue  # already on screen — don't reuse
            ph2 = _dhash(dest)
            if (ph2 is not None and any(
                    _ham(ph2, sph) <= DHASH_MAX_DIST
                    for sph, _ in seen_ph)):
                continue  # near-duplicate of something on screen
            v["path"] = str(dest)
            v["source"] = "screenshot"
            v["shot_url"] = rurl
            seen_exact[h2] = v["idx"]
            used_urls.add(rurl)
            if ph2 is not None:
                seen_ph.append((ph2, v["idx"]))
            print(f"[visuals] shot {v['idx']}: replaced with fresh "
                  f"screenshot '{rurl[:60]}'")
            return True
        return False

    seen_exact = {}  # sha256 -> shot idx
    seen_urls = {}   # screenshot page URL -> shot idx
    seen_ph = []     # [(dhash, idx)] for stills
    used_urls = {v.get("shot_url") for v in visuals if v.get("shot_url")}

    for v in visuals:
        p = v.get("path", "")
        if not p or not p.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        try:
            h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        except Exception:
            continue
        ph = _dhash(p)
        is_pin = v.get("source") == "verified-pin"

        dup_of = None
        reason = ""
        if h in seen_exact:
            dup_of, reason = seen_exact[h], "byte-identical file"
        elif v.get("shot_url") and v["shot_url"] in seen_urls:
            dup_of = seen_urls[v["shot_url"]]
            reason = f"same article screenshot ({v['shot_url'][:60]})"
        elif ph is not None:
            for sph, sidx in seen_ph:
                if _ham(ph, sph) <= DHASH_MAX_DIST:
                    dup_of, reason = sidx, "perceptual near-duplicate"
                    break

        if dup_of is None:
            seen_exact[h] = v["idx"]
            if v.get("shot_url"):
                seen_urls[v["shot_url"]] = v["idx"]
            if ph is not None:
                seen_ph.append((ph, v["idx"]))
            continue

        # Intentional reuse: a verified pin is a deliberate worker choice
        # for that exact query (e.g. the story logo in both the headline
        # and the deep-dive) — never replace it with a screenshot.
        if is_pin:
            print(f"[visuals] shot {v['idx']}: {reason} as shot {dup_of} "
                  f"but a verified pin — intentional reuse, keeping")
            continue

        print(f"[visuals] DUPLICATE IMAGE — shot {v['idx']} {reason} "
              f"as shot {dup_of}; replacing with a fresh screenshot")
        if not _replace_with_fresh_screenshot(v, used_urls,
                                              seen_exact, seen_ph):
            # Every source URL is already on screen or failed: flag
            # loudly for the frame review instead of shipping a repeat.
            print(f"[visuals] shot {v['idx']}: ERROR — no fresh visual "
                  f"available; marked duplicate-needs-review")
            v["source"] = "duplicate-needs-review"


if __name__ == "__main__":
    main()
