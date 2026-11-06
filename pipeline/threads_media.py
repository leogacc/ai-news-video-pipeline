#!/usr/bin/env python3
"""Extract media from a Threads post WITHOUT the connector (which is text-only).

Why this exists (2026-10-28): the Threads connector returns text-level data
only — no media files, no media URLs. Every clip build that needed a Threads
post's image or video therefore fell back to stills or stalled, even when the
post itself carried the best visual (e.g. kimmonismus's 2026-10-28 Gemini 4
Carbon post, whose benchmark-chart image was missed by the 11am scout run and
by the in-flight clip build until the user supplied the share link).

What works here (verified 2026-10-28):
  - IMAGE posts: fetch the post's /media viewer page and grep the scontent
    t51.82787-15 .jpg URLs out of the HTML. Downloadable directly.
  - VIDEO posts: the /media page contains NO mp4 URL — only a poster frame.
    Video still needs the browser embed-page download route (open
    /post/<code>/embed in the browser, use the player's native download
    control). This script reports that honestly instead of pretending.

Implementation note: page fetches go through curl, NOT Python urllib.
Threads serves Python's TLS fingerprint a reduced page with no media URLs
in it (verified: urllib got 259KB with zero scontent references; curl got
623KB including the photo URL). AND the User-Agent matters, counterintuitively:
a bare "Mozilla/5.0" gets the media-bearing page (615KB, photo URLs present),
while a full desktop Chrome UA gets a reduced 261KB shell with NO media URLs.
Do not "improve" the UA — that silently breaks extraction. Downloads also
go through curl.

Usage:
  python3 threads_media.py <post-url-or-code> [--out DIR] [--handle HANDLE]
  - Accepts a full post URL, a share URL (redirect is followed to the
    canonical post URL), or a bare post code (requires --handle).
  - Prints a JSON summary to stdout: canonical_url, post_code, media found,
    files downloaded, and what still needs the browser route.
  - Exit 0 even when no media is found (that is a result, not a failure);
    non-zero only on fetch errors.

Part of pipeline v2026.10.28.1. Used by the clips template footage hunt:
run this for a Threads-sourced pick BEFORE falling back to stills, and log
the attempt + result in the clip's meta.json.
"""

import html
import json
import os
import re
import subprocess
import sys

UA = "Mozilla/5.0"
PHOTO_RE = re.compile(r"https://scontent[^\"\\ ]*?t51\.82787-15[^\"\\ ]*?\.jpg[^\"\\ ]*")
POSTER_RE = re.compile(r"https://scontent[^\"\\ ]*?t51\.71878-15[^\"\\ ]*?\.jpg[^\"\\ ]*")
MP4_RE = re.compile(r"https://[^\"\\ ]*?\.mp4[^\"\\ ]*")


def curl_text(url, timeout=30):
    """Fetch a page via curl (see module note: urllib gets a reduced page)."""
    proc = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), "-A", UA, url],
        capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("curl failed (%d): %s"
                           % (proc.returncode, proc.stderr.strip()[:200]))
    return proc.stdout


def curl_effective_url(url, timeout=30):
    proc = subprocess.run(
        ["curl", "-s", "-L", "-o", "/dev/null", "-w", "%{url_effective}",
         "--max-time", str(timeout), "-A", UA, url],
        capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("curl failed (%d)" % proc.returncode)
    return proc.stdout.strip()


def curl_download(url, path, timeout=60):
    proc = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout), "-A", UA,
         "-o", path, url],
        capture_output=True, text=True, errors="replace")
    if proc.returncode != 0:
        raise RuntimeError("curl download failed (%d): %s"
                           % (proc.returncode, proc.stderr.strip()[:200]))
    return os.path.getsize(path)


def clean(url):
    return html.unescape(url).replace("\\u0026", "&").replace("&amp;", "&")


def main(argv):
    if len(argv) < 2:
        print("usage: threads_media.py <post-url-or-code> [--out DIR] "
              "[--handle HANDLE]", file=sys.stderr)
        return 2
    target, out_dir, handle = argv[1], None, None
    i = 2
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out_dir, i = argv[i + 1], i + 2
        elif argv[i] == "--handle" and i + 1 < len(argv):
            handle, i = argv[i + 1], i + 2
        else:
            i += 1

    if "/share/" in target:
        try:
            target = curl_effective_url(target)
        except RuntimeError as exc:
            print("share-link resolve failed: %s" % exc, file=sys.stderr)
            return 1

    m = re.search(r"/post/([A-Za-z0-9_-]+)", target)
    if m:
        code = m.group(1)
        hm = re.search(r"@([^/]+)/post/", target)
        if hm:
            handle = hm.group(1)
    elif re.match(r"^[A-Za-z0-9_-]+$", target) and handle:
        code = target
    else:
        print("cannot parse a post code from %r (pass a post URL or a bare "
              "code with --handle)" % target, file=sys.stderr)
        return 2

    post_url = ("https://www.threads.com/@%s/post/%s" % (handle, code)
                if handle else "https://www.threads.com/post/%s" % code)
    result = {"post_code": code, "canonical_url": post_url,
              "images": [], "poster": None, "video": None,
              "needs_browser_embed_route": False, "files": []}
    try:
        page = curl_text(post_url.rstrip("/") + "/media")
    except RuntimeError as exc:
        print("fetch failed for %s: %s" % (post_url, exc), file=sys.stderr)
        return 1

    photos = []
    for url in PHOTO_RE.findall(page):
        url = clean(url)
        if url not in photos:
            photos.append(url)
    posters = [clean(u) for u in POSTER_RE.findall(page)]
    mp4s = [clean(u) for u in MP4_RE.findall(page)]

    result["images"] = photos
    result["poster"] = posters[0] if posters else None
    result["video"] = mp4s[0] if mp4s else None
    if not photos and not mp4s:
        # No downloadable media in the page. If a poster exists, this is
        # most likely a video post whose file needs the browser embed route.
        result["needs_browser_embed_route"] = bool(posters)

    if out_dir and photos:
        os.makedirs(out_dir, exist_ok=True)
        for idx, url in enumerate(photos):
            fname = "%s_%d.jpg" % (code, idx) if len(photos) > 1 \
                else "%s.jpg" % code
            path = os.path.join(out_dir, fname)
            try:
                size = curl_download(url, path)
                result["files"].append({"path": path, "bytes": size})
            except RuntimeError as exc:
                result.setdefault("download_errors", []).append(
                    {"url": url[:100], "error": str(exc)})

    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
