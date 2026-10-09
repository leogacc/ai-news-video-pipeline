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


def slug(q: str) -> str:
    return hashlib.sha1(q.lower().encode()).hexdigest()[:12]


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


def microlink_screenshot(page_url: str):
    """Screenshot of a source article/post via Microlink.
    The documentary fallback: showing the actual source is always
    relevant and never a wrong visual. x.com pages get a narrow viewport
    so the screenshot is the post column, not the login sidebar."""
    try:
        params = {"url": page_url, "screenshot": "true",
                  "meta": "false", "waitForTimeout": 3000}
        if "x.com" in page_url or "twitter.com" in page_url:
            params["viewport.width"] = "900"
            params["viewport.height"] = "1400"
        r = requests.get("https://api.microlink.io", params=params,
                         timeout=90).json()
        if r.get("status") == "success":
            return ((r.get("data") or {}).get("screenshot") or {}).get("url")
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
                 idx: int, page_urls: list = None, prev_path: str = None):
    """Resolve one visual per the evidence/illustrative tier. Returns
    (kind, path, source). Source is explicit — a wrong or generic visual
    is a hallucination vector, so fallbacks are labeled, never silent.

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
    kind, path, source = None, None, None
    # Verified pins first (agent-searched, relevance-checked).
    for cand in (VCACHE / f"{slug(q)}.mp4", VCACHE / f"{slug(q)}.jpg"):
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
        # Documentary fallback: screenshot the actual source article/post.
        # Always relevant, never a wrong visual. On a quarantine retry the
        # first URL already failed QA, so start from the next one.
        urls = page_urls or []
        if _retry_mode() and len(urls) > 1:
            urls = urls[1:] + urls[:1]
        for purl in urls:
            if path:
                break
            surl = microlink_screenshot(purl)
            if surl:
                try:
                    dest = CACHE / f"screenshot_{slug(purl)}.jpg"
                    download(surl, dest)
                    if dest.stat().st_size > 10_000:
                        if "x.com" in purl or "twitter.com" in purl:
                            crop_x_screenshot(dest)
                        # 2026-10-09: adjacent shots screenshotting the same
                        # page got the byte-identical file and QA rejected
                        # the run. Vary the crop per shot — still the actual
                        # article, just a different band of the page — under
                        # a distinct path so consecutive shots never match.
                        if str(dest) == (prev_path or ""):
                            from PIL import Image
                            im = Image.open(dest).convert("RGB")
                            w0, h0 = im.size
                            band = int(h0 * 0.65)
                            top = 0 if idx % 2 == 0 else h0 - band
                            vdest = (CACHE /
                                     f"screenshot_{slug(purl)}_v{idx}.jpg")
                            im.crop((0, top, w0, top + band)).save(
                                vdest, quality=88)
                            dest = vdest
                            print(f"[visuals] shot {idx}: screenshot variant "
                                  f"crop (same page as previous shot)")
                        kind, path, source = "photo", str(dest), "screenshot"
                        print(f"[visuals] shot {idx}: screenshot "
                              f"'{purl[:60]}' -> photo")
                    else:
                        dest.unlink(missing_ok=True)
                except Exception as e:
                    print(f"[visuals] screenshot download failed: {e}")
    if path is None:
        path = str(ROOT / "output" / f"card_{idx:02d}.png")
        title_card(script_title, Path(path), w, h)
        kind, source = "card", "title-card"
        print(f"[visuals] shot {idx}: '{q}' -> title card fallback")
    # Evidence shots must never come from blind search — if one did, the
    # sourcing policy was bypassed. Flag it loudly instead of passing
    # silently.
    if vtype == "evidence" and source in ("pixabay", "photos", "videos",
                                          "pexels"):
        print(f"[visuals] shot {idx}: POLICY VIOLATION — blind {source} "
              f"used for evidence '{spec.get('visual_subject')}'")
    return kind, path, source


def main():
    import sys
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    script = json.loads((ROOT / "output" / "script.json").read_text())
    timings = json.loads((ROOT / "output" / "timings.json").read_text())
    words = json.loads((ROOT / "output" / "words.json").read_text())
    w, h = CFG[mode]["width"], CFG[mode]["height"]

    visuals = []

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
    for sid, src in zip(script.get("story_ids", []),
                        script.get("sources", [])):
        if sid:
            sid_to_urls[sid] = [u for u in (src.get("url"),
                                            src.get("x_media_url")) if u]
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
                    pinned = ("clip" if cand.suffix == ".mp4" else "photo",
                              str(cand))
                    break
            n = story_asset_n.get(sid, 0)
            assets = story_assets.get(sid, []) if sid else []
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
                kind, path, source = fetch_visual(sh, dur, w, h,
                                                 script["title"], idx,
                                                 page_urls, prev_path)
            entry = {"idx": idx, "segment": i, "kind": kind,
                     "path": path, "duration": round(dur, 3),
                     "seg_kind": seg_kind, "start": round(s_time, 3),
                     "source": source,
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
        if fw and fw > visuals[k]["start"] + 0.05:
            shift = round(fw - visuals[k]["start"], 3)
            if visuals[k]["duration"] - shift >= 0.8:
                visuals[k - 1]["duration"] = round(
                    visuals[k - 1]["duration"] + shift, 3)
                visuals[k]["start"] = round(fw, 3)
                visuals[k]["duration"] = round(
                    visuals[k]["duration"] - shift, 3)
                print(f"[visuals] shot {visuals[k]['idx']}: cut aligned to "
                      f"speech (+{shift:.2f}s)")
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
    (ROOT / "output" / "visuals.json").write_text(json.dumps(visuals, indent=2))
    print(f"[visuals] {len(visuals)} shots planned")


if __name__ == "__main__":
    main()
