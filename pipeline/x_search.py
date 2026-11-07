"""Production Free X Search & Ingestion Engine.

Zero-cost, unauthenticated X search, VIP timeline monitoring, and media hydration:
1. VIP Account Timelines: Twitter Syndication Timeline Profile API.
2. Keyword Search: Google News RSS with site:x.com filter.
3. Media Hydration: Twitter Syndication CDN (direct 1080p MP4s from video.twimg.com).
4. Fallback: fxtwitter API.
"""
import argparse
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def _http_get(url: str, timeout: int = 15, headers: dict = None) -> tuple[int, bytes, float]:
    """Execute HTTP GET returning (status_code, body, elapsed_seconds)."""
    # NOTE: In this VM environment, curl handles SSL fingerprints cleanly
    t0 = time.perf_counter()
    cmd = [
        "curl", "-s", "-L", "--max-time", str(timeout),
        "-A", (headers.get("User-Agent") if headers else USER_AGENT),
        url
    ]
    if headers:
        for k, v in headers.items():
            if k.lower() != "user-agent":
                cmd.extend(["-H", f"{k}: {v}"])
    r = subprocess.run(cmd, capture_output=True, timeout=timeout + 5)
    elapsed = time.perf_counter() - t0
    # Inspect HTTP status code if needed or check stdout
    if r.returncode != 0:
        return 0, r.stderr or b"curl failed", elapsed
    return 200, r.stdout, elapsed


def fetch_user_timeline(handle: str, max_tweets: int = 100) -> list[dict]:
    """Fetch unauthenticated timeline of an X account via Twitter Syndication."""
    handle = handle.lstrip("@").strip()
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
    status, body, elapsed = _http_get(url, timeout=15)
    if status != 200 or not body:
        return []

    try:
        html_text = body.decode("utf-8", errors="replace")
    except Exception:
        return []

    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text)
    if not m:
        # Resilient fallback: Query Google News RSS for this handle when Syndication CDN is rate limited
        rss_hits = search_google_news_x(f"site:x.com/{handle}", max_results=max_tweets)
        fallback_results = []
        for h in rss_hits:
            fallback_results.append({
                "id": f"gnews_{int(time.time()*1000)}_{len(fallback_results)}",
                "author_handle": handle,
                "author_name": handle,
                "author_verified": True,
                "author_badge_type": "blue",
                "author_avatar": "",
                "text": h.get("title", ""),
                "media_urls": [],
                "url": h.get("link", f"https://x.com/{handle}"),
                "date": h.get("pub_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            })
        return fallback_results

    try:
        data = json.loads(m.group(1))
    except Exception:
        return []

    tl = data.get("props", {}).get("pageProps", {}).get("timeline", {})
    entries = tl.get("entries") or []
    results = []

    for entry in entries[:max_tweets]:
        tw = entry.get("content", {}).get("tweet", {})
        if not tw:
            continue
        tw_id = tw.get("id_str")
        if not tw_id:
            continue

        u = tw.get("user", {})
        text = tw.get("full_text") or tw.get("text") or ""
        text = html.unescape(text).strip()

        # Extract media URLs
        media_entities = tw.get("entities", {}).get("media") or []
        media_urls = [m.get("media_url_https") for m in media_entities if m.get("media_url_https")]

        # Determine verified status and badge type
        is_blue = u.get("is_blue_verified", False)
        is_ver = u.get("verified", False) or is_blue
        badge_type = "organization" if u.get("profile_image_shape") == "Square" else (
            "blue" if is_ver else None
        )

        avatar = u.get("profile_image_url_https", "")
        if "_normal." in avatar:
            avatar = avatar.replace("_normal.", "_400x400.")

        created_at = tw.get("created_at", "")

        results.append({
            "id": tw_id,
            "author_handle": u.get("screen_name") or handle,
            "author_name": u.get("name") or handle,
            "author_verified": is_ver,
            "author_badge_type": badge_type,
            "author_avatar": avatar,
            "text": text,
            "created_at": created_at,
            "url": f"https://x.com/{u.get('screen_name') or handle}/status/{tw_id}",
            "likes": int(tw.get("favorite_count") or 0),
            "retweets": int(tw.get("retweet_count") or 0),
            "replies": int(tw.get("reply_count") or 0),
            "has_media": bool(media_urls),
            "media_urls": media_urls,
        })

    return results


def search_google_news_x(query: str, max_results: int = 50) -> list[dict]:
    """Search X posts using Google News RSS with site:x.com filtering."""
    encoded_q = urllib.parse.quote(f"site:x.com {query}")
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
    status, body, elapsed = _http_get(url, timeout=12)
    if status != 200 or not body:
        return []

    try:
        root = ET.fromstring(body)
    except Exception:
        return []

    items = root.findall(".//item")
    results = []

    for it in items[:max_results]:
        title = it.findtext("title", "")
        link = it.findtext("link", "")
        pub_date = it.findtext("pubDate", "")
        source = it.findtext("source", "")

        # Extract possible handle or status ID from title/description
        # Google News often formats title as "Headline / Post Text - Author (@handle) on X"
        handle_match = re.search(r"@(\w{1,15})", title)
        detected_handle = handle_match.group(1) if handle_match else ""

        results.append({
            "title": html.unescape(title),
            "link": link,
            "pub_date": pub_date,
            "source": source,
            "detected_handle": detected_handle,
        })

    return results


def search_hn_ai_dispatches(query: str, max_results: int = 15) -> list[dict]:
    """Search Hacker News Algolia API for high-signal AI story discussions and links."""
    encoded_q = urllib.parse.quote(query)
    url = f"https://hn.algolia.com/api/v1/search_by_date?query={encoded_q}&tags=story&hitsPerPage={max_results}"
    status, body, elapsed = _http_get(url, timeout=10)
    if status != 200 or not body:
        return []

    try:
        data = json.loads(body.decode("utf-8"))
    except Exception:
        return []

    hits = data.get("hits") or []
    results = []
    for h in hits:
        url_val = h.get("url") or ""
        results.append({
            "title": h.get("title", ""),
            "url": url_val,
            "points": h.get("points") or 0,
            "comments": h.get("num_comments") or 0,
            "author": h.get("author", ""),
            "created_at": h.get("created_at", ""),
            "is_x_link": "x.com" in url_val or "twitter.com" in url_val,
        })
    return results


def hydrate_tweet_details(tweet_id: str, handle: str = "") -> dict:
    """Hydrate full tweet metadata, media assets, and video streams from Syndication CDN."""
    tweet_id = str(tweet_id).strip()
    syn_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=x"
    status, body, _ = _http_get(syn_url, timeout=10)

    data = None
    if status == 200 and body:
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            data = None

    # Fallback to fxtwitter if syndication fails
    if not data or not (data.get("text") or data.get("id_str")):
        fx_handle = handle or "i"
        fx_url = f"https://api.fxtwitter.com/{fx_handle}/status/{tweet_id}"
        f_status, f_body, _ = _http_get(fx_url, timeout=10)
        if f_status == 200 and f_body:
            try:
                f_json = json.loads(f_body.decode("utf-8"))
                t = f_json.get("tweet", {})
                if t.get("text"):
                    return _normalize_fxtwitter_payload(t, tweet_id)
            except Exception:
                pass
        raise ValueError(f"Failed to hydrate tweet {tweet_id} from all sources")

    return _normalize_syndication_payload(data, tweet_id)


def _normalize_syndication_payload(data: dict, tweet_id: str) -> dict:
    user = data.get("user") or {}
    is_blue = user.get("is_blue_verified", False)
    is_ver = user.get("verified", False) or is_blue
    badge_type = "organization" if user.get("profile_image_shape") == "Square" else (
        "blue" if is_ver else None
    )

    avatar_url = user.get("profile_image_url_https", "")
    if "_normal." in avatar_url:
        avatar_url = avatar_url.replace("_normal.", "_400x400.")

    text = data.get("text", "")
    text = html.unescape(text).replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

    photos = []
    videos = []

    for md in (data.get("mediaDetails") or []):
        mtype = md.get("type")
        murl = md.get("media_url_https")
        if mtype == "photo" and murl:
            photos.append(murl)
        elif mtype in ("video", "animated_gif"):
            vinfo = md.get("video_info", {})
            variants = vinfo.get("variants", [])
            mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
            mp4s.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
            videos.append({
                "duration_ms": vinfo.get("duration_millis"),
                "variants": mp4s,
                "best_mp4": mp4s[0].get("url") if mp4s else None,
                "best_bitrate": mp4s[0].get("bitrate") if mp4s else 0,
                "poster_url": murl,
            })

    views_val = data.get("views", 0)
    if isinstance(views_val, dict):
        views_val = views_val.get("count", 0)

    return {
        "id": data.get("id_str", tweet_id),
        "text": text,
        "created_at": data.get("created_at", ""),
        "author": {
            "name": user.get("name", "X User"),
            "screen_name": user.get("screen_name", "x"),
            "avatar_url": avatar_url,
            "verified": is_ver,
            "badge_type": badge_type,
        },
        "metrics": {
            "likes": int(data.get("favorite_count") or 0),
            "retweets": int(data.get("retweet_count") or 0),
            "replies": int(data.get("reply_count") or 0),
            "views": int(views_val or 0),
        },
        "photos": photos,
        "videos": videos,
        "source": "syndication_cdn",
    }


def _normalize_fxtwitter_payload(t: dict, tweet_id: str) -> dict:
    a = t.get("author") or {}
    v = a.get("verification") or {}
    is_ver = v.get("verified", False)
    vtype = v.get("type") or ("blue" if is_ver else None)

    media = t.get("media") or {}
    photos = [p.get("url") for p in (media.get("photos") or []) if p.get("url")]
    videos = []

    for vid in (media.get("videos") or []):
        vurl = vid.get("url")
        if vurl:
            videos.append({
                "duration_ms": vid.get("duration", 0) * 1000 if vid.get("duration") else None,
                "variants": [{"url": vurl, "content_type": "video/mp4", "bitrate": 0}],
                "best_mp4": vurl,
                "best_bitrate": 0,
                "poster_url": vid.get("thumbnail_url"),
            })

    return {
        "id": t.get("id", tweet_id),
        "text": t.get("text", ""),
        "created_at": t.get("created_at", ""),
        "author": {
            "name": a.get("name", "X User"),
            "screen_name": a.get("screen_name", "x"),
            "avatar_url": a.get("avatar_url", ""),
            "verified": is_ver,
            "badge_type": vtype,
        },
        "metrics": {
            "likes": int(t.get("likes") or 0),
            "retweets": int(t.get("retweets") or 0),
            "replies": int(t.get("replies") or 0),
            "views": int(t.get("views") or 0),
        },
        "photos": photos,
        "videos": videos,
        "source": "fxtwitter",
    }


def download_tweet_video(tweet_details: dict, dest_path: Path) -> Path | None:
    """Download the highest bitrate MP4 video attached to a tweet."""
    videos = tweet_details.get("videos") or []
    if not videos or not videos[0].get("best_mp4"):
        return None

    mp4_url = videos[0]["best_mp4"]
    dest_path = Path(dest_path).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["curl", "-s", "-L", "--max-time", "60", "-A", USER_AGENT, mp4_url, "-o", str(dest_path)]
    r = subprocess.run(cmd, timeout=70)
    if r.returncode == 0 and dest_path.exists() and dest_path.stat().st_size > 20_000:
        return dest_path
    return None


def download_tweet_photos(tweet_details: dict, dest_dir: Path) -> list[Path]:
    """Download all photos attached to a tweet into the destination directory."""
    dest_dir = Path(dest_dir).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    tw_id = tweet_details.get("id", "photo")
    saved = []

    for i, p_url in enumerate(tweet_details.get("photos") or []):
        p_path = dest_dir / f"photo_{tw_id}_{i+1}.jpg"
        cmd = ["curl", "-s", "-L", "--max-time", "30", "-A", USER_AGENT, p_url, "-o", str(p_path)]
        r = subprocess.run(cmd, timeout=35)
        if r.returncode == 0 and p_path.exists() and p_path.stat().st_size > 5_000:
            saved.append(p_path)

    return saved


def dedupe_check(post_id: str, state: dict, saved_items: list, clipped_finds: list) -> bool:
    """Return True if post_id is already in seen, saved, or clipped state."""
    sid = str(post_id).strip()
    # 1. State seen
    seen_ids = set(state.get("seen_post_ids", []))
    if sid in seen_ids:
        return True

    # 2. Saved items pool
    for item in saved_items:
        if str(item.get("post_id", "")).strip() == sid:
            return True

    # 3. Clipped finds
    for clip in clipped_finds:
        if str(clip.get("post_id", "")).strip() == sid:
            return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Free X Search & Ingestion Engine")
    parser.add_argument("--handle", help="Fetch timeline for an X account handle")
    parser.add_argument("--search", help="Execute Google News RSS keyword search")
    parser.add_argument("--tweet", help="Hydrate details for a specific tweet status ID")
    parser.add_argument("--download-video", action="store_true", help="Download video for hydrated tweet")
    parser.add_argument("--limit", type=int, default=10, help="Max results to display")
    parser.add_argument("--out", help="Output path for video download")
    args = parser.parse_args()

    if args.handle:
        print(f"Fetching timeline for @{args.handle}...")
        tweets = fetch_user_timeline(args.handle, max_tweets=args.limit)
        print(f"Found {len(tweets)} tweets:")
        for t in tweets:
            badge = f" [{t['author_badge_type']}]" if t['author_badge_type'] else ""
            print(f"  [{t['id']}] {t['created_at']} | Likes: {t['likes']}{badge}")
            print(f"    {t['text'][:100]}...\n")

    elif args.search:
        print(f"Searching for '{args.search}' on X via Google News RSS...")
        hits = search_google_news_x(args.search, max_results=args.limit)
        print(f"Found {len(hits)} hits:")
        for h in hits:
            print(f"  - {h['title']}")
            print(f"    {h['link']}\n")

    elif args.tweet:
        print(f"Hydrating tweet {args.tweet}...")
        details = hydrate_tweet_details(args.tweet)
        print(f"Author: {details['author']['name']} (@{details['author']['screen_name']})")
        print(f"Text  : {details['text']}")
        print(f"Likes : {details['metrics']['likes']} | Photos: {len(details['photos'])} | Videos: {len(details['videos'])}")

        if args.download_video and details.get("videos"):
            out_file = Path(args.out) if args.out else Path(f"/tmp/video_{args.tweet}.mp4")
            print(f"Downloading video to {out_file}...")
            res = download_tweet_video(details, out_file)
            if res:
                print(f"[OK] Video downloaded: {res} ({round(res.stat().st_size/1024, 1)} KB)")
            else:
                print("[FAIL] Failed to download video")


if __name__ == "__main__":
    main()
