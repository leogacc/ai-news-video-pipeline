"""Render a faithful X-post card from a tweet URL.

2026-10-19 v1 (user: X post screenshots badly cropped): x.com URLs were
never screenshotted — oEmbed + hand-rolled PIL card.
2026-10-19 v2 (user: "why don't they look exactly like x posts?"):
PIL card upgraded with real avatars, verified badge, action icons.
2026-10-19 v3 (user: "the x posts you made look ugly — there's got to be
a better open source project that gets a clean image of it"):
rewritten around Vercel's react-tweet philosophy (MIT) — fetch the real
tweet payload (fxtwitter API: author, avatar, verified type, counts,
photos) and render X's own dark-embed styling as self-contained HTML,
rasterized with headless Chromium at 2x. No network inside the browser:
avatar/photos are inlined as data URIs. Falls back to the PIL renderer
if anything fails.

Usage:
    python3 tweet_card.py "https://x.com/AnthropicAI/status/123..." [out.png]
"""
import base64
import html
import io
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RENDER_MJS = ROOT / "tweetshot" / "render.mjs"
NODE = "/usr/bin/node"

ACCENT = "#1d9bf0"
TEXT = "#e7e9ea"
SUBTLE = "#71767b"
BORDER = "#2f3336"
GOLD = "#ffd400"


def _get(url: str, timeout: int = 25) -> bytes:
    # NOTE: api.fxtwitter.com's CDN kills Python TLS fingerprints
    # (urllib -> 403/closed, requests -> truncated chunk); curl works.
    r = subprocess.run(
        ["curl", "-s", "--max-time", str(timeout),
         "-A", "Mozilla/5.0", url],
        capture_output=True, timeout=timeout + 10)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"fetch failed: {url[:80]}")
    return r.stdout


def _tweet_id(tweet_url: str) -> str:
    m = re.search(r"(?:x|twitter)\.com/([^/?#]+)/status/(\d+)", tweet_url)
    if not m:
        raise ValueError(f"not a tweet URL: {tweet_url}")
    return m.group(1), m.group(2)


def _fetch_fxtwitter(handle: str, sid: str) -> dict:
    # fxtwitter rate-limits per IP under burst use; retry once after a
    # pause. Raises if still blocked — caller falls back to oEmbed.
    last = None
    for attempt in range(3):
        try:
            raw = _get(f"https://api.fxtwitter.com/{handle}/status/{sid}")
            t = json.loads(raw.decode("utf-8")).get("tweet", {})
            if t.get("text"):
                return t
            last = ValueError("fxtwitter returned no text")
        except Exception as e:
            last = e
        if attempt < 2:
            import time
            time.sleep(45)
    raise last or RuntimeError("fxtwitter blocked")


def _fetch_oembed_fallback(tweet_url: str) -> dict:
    """publish.twitter.com oEmbed: author, handle, text, date. No counts,
    no avatar URL — avatar resolved via unavatar.io at render time."""
    api = ("https://publish.twitter.com/oembed?url=" +
           urllib.request.quote(tweet_url, safe="") + "&omit_script=true")
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    author_url = data.get("author_url", "")
    m = re.search(r"x\.com/([^/?#]+)", author_url)
    screen_name = m.group(1) if m else "x"
    raw_html = data.get("html", "")
    pm = re.search(r"<p[^>]*>(.*?)</p>", raw_html, re.S)
    text = pm.group(1) if pm else ""
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).strip()
    dm = re.search(r">([^<]+)</a>(?:</blockquote>)?\s*$", raw_html.strip())
    date = html.unescape(dm.group(1)).strip() if dm else ""
    return {
        "text": text,
        "created_at": date,  # already "October 18, 2026" style
        "author": {
            "name": data.get("author_name", "X User"),
            "screen_name": screen_name,
            "avatar_url": f"https://unavatar.io/x/{screen_name}",
            "verification": {"verified": False},
        },
    }


def _data_uri(url: str, max_bytes: int = 2_000_000) -> str | None:
    try:
        blob = _get(url, timeout=20)
        if len(blob) > max_bytes:
            return None
        mime = "image/jpeg" if url.lower().endswith((".jpg", ".jpeg")) \
            else "image/png"
        if blob[:8].startswith(b"\x89PNG"):
            mime = "image/png"
        return f"data:{mime};base64," + base64.b64encode(blob).decode()
    except Exception:
        return None


def _fmt_count(n) -> str:
    try:
        n = int(n or 0)
    except (TypeError, ValueError):
        return ""
    if n >= 1_000_000:
        s = f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{s}M"
    if n >= 1_000:
        s = f"{n / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{s}K"
    return str(n)


def _fmt_date(created_at: str) -> str:
    # "Sun Oct 18 18:07:51 +0000 2026" -> "6:07 PM · Oct 18, 2026".
    # oEmbed fallback already yields "October 18, 2026" — pass through.
    if re.match(r"^[A-Z][a-z]+ \d{1,2}, \d{4}$", (created_at or "").strip()):
        return created_at.strip()
    try:
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        dt = dt.astimezone(timezone.utc)
        h = dt.strftime("%I").lstrip("0") or "0"
        return f"{h}:{dt.strftime('%M %p')} · {dt.strftime('%b')} " \
               f"{dt.day}, {dt.year}"
    except Exception:
        return created_at or ""


def _linkify(text: str) -> str:
    esc = html.escape(text)
    # URLs, @mentions, #hashtags in X blue
    esc = re.sub(r"(https?://[^\s<]+)",
                 r'<span class="lnk">\1</span>', esc)
    esc = re.sub(r"(?<![\w/])@(\w{1,15})",
                 r'<span class="lnk">@\1</span>', esc)
    esc = re.sub(r"(?<![\w/])#(\w+)",
                 r'<span class="lnk">#\1</span>', esc)
    return esc.replace("\n", "<br>")


def _badge_svg(vtype: str | None) -> str:
    if not vtype:
        return ""
    color = GOLD if vtype == "organization" else ACCENT
    return (
        f'<svg class="badge" viewBox="0 0 24 24" width="22" height="22">'
        f'<circle cx="12" cy="12" r="10" fill="{color}"/>'
        '<path d="M10.2 15.4l-3.1-3.1 1.4-1.4 1.7 1.7 4.5-4.5 1.4 1.4z"'
        ' fill="#000"/></svg>'
    )


# X's own action icons (24x24, filled) — reply, repost, like, views,
# bookmark, share. Simplified but geometrically true to X's set.
ICONS = {
    "reply": '<path d="M1.75 10c0-4.42 3.58-8 8-8h4.37c4.49 0 8.13 3.64 8.13 '
             '8.13 0 2.96-1.61 5.68-4.2 7.11l-8.05 4.46v-3.69h-.07c-4.49.1-'
             '8.18-3.51-8.18-8.01zm8-6c-3.32 0-6 2.69-6 6 0 3.37 2.77 6.08 '
             '6.14 6.01l.35-.01h1.76v2.3l5.09-2.81c1.86-1.03 3.05-2.99 '
             '3.05-5.11 0-3.39-2.74-6.13-6.13-6.13H9.75z"/>',
    "repost": '<path d="M4.5 3.88l4.43 4.14-1.36 1.46L5.5 7.55V16c0 1.1.9 '
              '2 2 2H13v2H7.5c-2.21 0-4-1.79-4-4V7.55L1.43 9.48.07 8.02 '
              '4.5 3.88zM16.5 6H11V4h5.5c2.21 0 4 1.79 4 4v8.45l2.07-1.93 '
              '1.36 1.46-4.43 4.14-4.43-4.14 1.36-1.46 2.07 1.93V8c0-1.1-.9-2-2-2z"/>',
    "like": '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 '
            '2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 '
            '3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 '
            '11.54L12 21.35z"/>',
    "views": '<path d="M8.75 21V3h2v18h-2zM4 21V10h2v11H4zM13.5 21V6h2v15h-2zM18.25 '
             '21V11h2v10h-2z"/>',
    "bookmark": '<path d="M6 3h12a1 1 0 0 1 1 1v17.3a.5.5 0 0 1-.77.42L12 '
                '17.7l-6.23 4.02a.5.5 0 0 1-.77-.42V4a1 1 0 0 1 1-1zm1 '
                '2v13.6l5-3.22 5 3.22V5H7z"/>',
    "share": '<path d="M12 2.5l6 6-1.4 1.4-3.6-3.6V16h-2V6.3L7.4 9.9 6 '
             '8.5l6-6zM5 16v3.5A1.5 1.5 0 0 0 6.5 21h11a1.5 1.5 0 0 0 '
             '1.5-1.5V16h-2v3.5a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5V16H5z"/>',
}


def _icon(name: str) -> str:
    return (f'<svg class="ic" viewBox="0 0 24 24" width="23" height="23" '
            f'fill="{SUBTLE}">{ICONS[name]}</svg>')


def _build_html(t: dict) -> str:
    a = t.get("author", {})
    name = html.escape(a.get("name", "X User"))
    handle = "@" + html.escape(a.get("screen_name", "x"))
    v = (a.get("verification") or {})
    badge = _badge_svg(v.get("type") if v.get("verified") else None)

    avatar = _data_uri(a.get("avatar_url", "")) or ""
    avatar_tag = (f'<img class="avatar" src="{avatar}">'
                  if avatar else '<div class="avatar ph"></div>')

    text_html = _linkify(t.get("text", ""))

    media_html = ""
    photos = []
    media = t.get("media") or {}
    for p in (media.get("photos") or [])[:4]:
        uri = _data_uri(p.get("url", ""))
        if uri:
            photos.append(uri)
    if photos:
        cls = f"media-grid n{len(photos)}"
        imgs = "".join(f'<img src="{u}">' for u in photos)
        media_html = f'<div class="{cls}">{imgs}</div>'

    date_str = _fmt_date(t.get("created_at", ""))
    views = _fmt_count(t.get("views"))
    meta = (f'{html.escape(date_str)}'
            + (f' &nbsp;·&nbsp; <b>{views}</b> Views' if views and views != "0"
               else ""))

    def act(icon, count):
        c = _fmt_count(count)
        # oEmbed fallback has no counts — show the icon alone rather
        # than a wrong "0".
        span = f"<span>{c}</span>" if c and c != "0" else ""
        return (f'<div class="action">{_icon(icon)}'
                f'{span}</div>')

    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#000; display:flex; justify-content:center; padding:8px; }}
  #tweet-card {{
    width:1064px; background:#000; border:1px solid {BORDER};
    border-radius:16px; padding:20px 20px 12px 20px;
    font-family:"Noto Sans",-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    color:{TEXT};
  }}
  .header {{ display:flex; align-items:center; gap:14px; margin-bottom:14px; }}
  .avatar {{ width:52px; height:52px; border-radius:50%; object-fit:cover; flex:none; }}
  .avatar.ph {{ background:#333639; }}
  .names {{ flex:1; min-width:0; }}
  .name-row {{ display:flex; align-items:center; gap:6px; }}
  .name {{ font-size:21px; font-weight:700; color:{TEXT}; white-space:nowrap;
           overflow:hidden; text-overflow:ellipsis; }}
  .badge {{ flex:none; }}
  .handle {{ font-size:17px; color:{SUBTLE}; margin-top:2px; }}
  .xmark {{ flex:none; width:30px; height:30px; fill:{TEXT}; opacity:.9; }}
  .text {{ font-size:21px; line-height:1.45; color:{TEXT};
           overflow-wrap:break-word; margin-bottom:14px; }}
  .lnk {{ color:{ACCENT}; }}
  .media-grid {{ display:grid; gap:4px; margin-bottom:14px; border-radius:14px;
                 overflow:hidden; border:1px solid {BORDER}; }}
  .media-grid.n1 {{ grid-template-columns:1fr; }}
  .media-grid.n2 {{ grid-template-columns:1fr 1fr; }}
  .media-grid.n3 {{ grid-template-columns:1fr 1fr; }}
  .media-grid.n4 {{ grid-template-columns:1fr 1fr; }}
  .media-grid img {{ width:100%; height:100%; object-fit:cover; display:block;
                     max-height:520px; }}
  .meta {{ font-size:17px; color:{SUBTLE}; margin-bottom:12px; }}
  .meta b {{ color:{TEXT}; font-weight:700; }}
  .divider {{ border-top:1px solid {BORDER}; margin:0 -20px 4px -20px; }}
  .actions {{ display:flex; align-items:center; padding:6px 0 2px 0; }}
  .action {{ display:flex; align-items:center; gap:10px; width:25%; color:{SUBTLE}; }}
  .action span {{ font-size:16px; }}
  .spacer {{ flex:1; }}
  .action.tail {{ width:auto; margin-left:26px; }}
</style></head><body>
<div id="tweet-card">
  <div class="header">
    {avatar_tag}
    <div class="names">
      <div class="name-row"><span class="name">{name}</span>{badge}</div>
      <div class="handle">{handle}</div>
    </div>
    <svg class="xmark" viewBox="0 0 24 24"><path d="M18.9 1.15h3.68l-8.04 9.19L24 22.85h-7.41l-5.8-7.58-6.64 7.58H.47l8.6-9.83L0 1.15h7.59l5.24 6.93 6.07-6.93zm-1.29 19.5h2.04L6.49 3.24H4.3l13.31 17.41z"/></svg>
  </div>
  <div class="text">{text_html}</div>
  {media_html}
  <div class="meta">{meta}</div>
  <div class="divider"></div>
  <div class="actions">
    {act("reply", t.get("replies"))}
    {act("repost", t.get("retweets"))}
    {act("like", t.get("likes"))}
    {act("views", t.get("views"))}
    <div class="spacer"></div>
    <div class="action tail">{_icon("bookmark")}</div>
    <div class="action tail">{_icon("share")}</div>
  </div>
</div>
</body></html>"""


def _render_html_card(tweet_url: str, out_path: Path) -> Path:
    handle, sid = _tweet_id(tweet_url)
    try:
        t = _fetch_fxtwitter(handle, sid)
    except Exception as e:
        print(f"[tweet_card] fxtwitter blocked ({e}) — oEmbed fallback")
        t = _fetch_oembed_fallback(tweet_url)
    if not t.get("text"):
        raise ValueError("no tweet text from any source")
    page = _build_html(t)
    html_path = out_path.with_suffix(".html").resolve()
    out_path = out_path.resolve()
    html_path.write_text(page, encoding="utf-8")
    cmd = [NODE, str(RENDER_MJS), str(html_path), "#tweet-card",
           str(out_path), "1080"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if r.returncode != 0 or not out_path.exists() \
            or out_path.stat().st_size < 20_000:
        raise RuntimeError(f"headless render failed: "
                           f"{r.stderr[-300:] or r.stdout[-300:]}")
    print(f"[tweet_card] {t['author'].get('name')} "
          f"@{t['author'].get('screen_name')}: html card -> {out_path}")
    return out_path


def _render_pil(tweet_url: str, out_path: Path) -> Path:
    """2026-10-19 v2 PIL fallback — kept for offline emergencies."""
    from PIL import Image, ImageDraw, ImageFont
    W, PAD = 1080, 44
    BG, TEXTc, SUBTLEc = (0, 0, 0), (231, 233, 234), (113, 118, 123)
    img = Image.new("RGB", (W, 400), BG)
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 40)
    except OSError:
        f = ImageFont.load_default()
    d.text((PAD, PAD), "X post (render unavailable)", font=f, fill=TEXTc)
    d.text((PAD, PAD + 70), tweet_url[:60], font=f, fill=SUBTLEc)
    img.save(out_path)
    return out_path


def render_tweet_card(tweet_url: str, out_path) -> Path:
    """Fetch tweet and render a faithful X dark-mode card."""
    out_path = Path(out_path)
    try:
        return _render_html_card(tweet_url, out_path)
    except Exception as e:
        print(f"[tweet_card] html render failed ({e}) — PIL fallback")
        return _render_pil(tweet_url, out_path)


if __name__ == "__main__":
    url = sys.argv[1]
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tweet_card.png")
    render_tweet_card(url, out)
