#!/usr/bin/env python3
"""SCOUT — fetch AI news from free RSS sources, dedupe, rank. -> output/stories.json

Sources: Google News RSS (no key needed) + optional hand-curated override file
`input/stories_override.json` (e.g. picks from the morning digest). Override
stories are always preferred when fresh.
"""
import feedparser
import hashlib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

QUERIES = [
    "artificial intelligence",
    "AI model launch",
    "generative AI breakthrough",
]

# Hacker News (Algolia API): free, no key, server-friendly. Gives direct
# publisher URLs + points as a quality signal — the reliable way to get
# fetchable article links, since Google News redirect URLs can't be
# resolved and publisher RSS feeds block datacenter IPs.
HN_QUERIES = ["AI", "artificial intelligence", "LLM"]

MAX_PER_QUERY = 8
MAX_PER_HN_QUERY = 8


def norm_id(title: str) -> str:
    t = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", title.lower())).strip()
    return hashlib.sha1(t.encode()).hexdigest()[:16]


def fetch_gnews(query: str):
    q = urllib.parse.quote(query)
    url = (f"https://news.google.com/rss/search?q={q}%20when%3A3d"
           f"&hl=en-US&gl=US&ceid=US:en")
    feed = feedparser.parse(url)
    stories = []
    for e in feed.entries[:MAX_PER_QUERY]:
        title = html.unescape(getattr(e, "title", "")).strip()
        if not title:
            continue
        # Google News titles look like "Headline - Source"; split the source off.
        if " - " in title:
            title, source = title.rsplit(" - ", 1)
        else:
            source = getattr(getattr(e, "source", None), "title", "Google News")
        published = getattr(e, "published", "")
        stories.append({
            "id": norm_id(title),
            "title": title,
            "summary": html.unescape(re.sub(r"<[^>]+>", " ", getattr(e, "summary", ""))).strip()[:600],
            "url": getattr(e, "link", ""),
            "source": source,
            "published": published,
            "curated": False,
        })
    return stories


def load_override():
    """Hand-picked stories (e.g. from the morning AI digest) win over RSS."""
    p = ROOT / "input" / "stories_override.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
    except Exception:
        return []
    fresh = []
    for s in data.get("stories", []):
        ts = s.get("added_at", "")
        try:
            age_h = (datetime.now(timezone.utc) -
                     datetime.fromisoformat(ts)).total_seconds() / 3600
        except Exception:
            age_h = 999
        if age_h <= 36:  # stale overrides are ignored
            s = dict(s)
            s.setdefault("id", norm_id(s.get("title", "")))
            s["curated"] = True
            fresh.append(s)
    return fresh


def fetch_hn(query: str, limit: int):
    """Top recent AI stories from Hacker News (Algolia API)."""
    try:
        since = int(time.time()) - 3 * 86400
        params = urllib.parse.urlencode({
            "query": query, "tags": "story", "hitsPerPage": limit,
            "numericFilters": f"created_at_i>{since},points>15",
        })
        req = urllib.request.Request(
            "https://hn.algolia.com/api/v1/search?" + params,
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f"[scout] HN query failed ({query}): {e}")
        return []
    stories = []
    for h in data.get("hits", []):
        title = html.unescape(h.get("title") or "").strip()
        link = (h.get("url") or "").strip()
        if not title or not link:
            continue
        if not link.startswith(("http://", "https://")):
            continue
        domain = urllib.parse.urlparse(link).netloc.replace("www.", "")
        stories.append({
            "id": norm_id(title + link),
            "title": title,
            "summary": f"HN discussion ({h.get('points', 0)} points, "
                       f"{h.get('num_comments', 0)} comments).",
            "url": link,
            "source": f"Hacker News via {domain}",
            "published": h.get("created_at", ""),
            "curated": False,
        })
    return stories


def strip_html(raw: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_article(url: str, max_chars: int = 6000) -> str:
    """Full article text. Tries trafilatura (direct) first, then Microlink
    (server-side fetch + extraction, free tier) as fallback. Returns ""
    on any failure — the writer then stays strictly within the
    headline/summary instead of inventing details."""
    if not url or "news.google.com" in url:
        return ""
    text = ""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False) or ""
    except Exception:
        pass
    if len(text.strip()) < 500:
        # Microlink fallback: their servers fetch the page, we extract
        # the main/article/body content and strip tags ourselves.
        try:
            for sel in ("main", "article", "body"):
                params = urllib.parse.urlencode({
                    "url": url, "data.text.selector": sel,
                    "data.text.type": "text"})
                req = urllib.request.Request(
                    "https://api.microlink.io/?" + params,
                    headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.load(resp)
                chunk = ((data.get("data") or {}).get("text")) or ""
                if len(chunk) > len(text):
                    text = strip_html(chunk)
                if len(text.strip()) >= 500:
                    break
        except Exception as e:
            print(f"[scout] microlink failed ({url[:60]}): {e}")
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    return text[:max_chars]


def main():
    seen = set()
    state_p = ROOT / "state.json"
    if state_p.exists():
        try:
            seen = set(json.loads(state_p.read_text()).get("seen_ids", []))
        except Exception:
            pass

    stories = []
    for q in QUERIES:
        try:
            stories.extend(fetch_gnews(q))
        except Exception as e:
            print(f"[scout] query failed ({q}): {e}")
    for q in HN_QUERIES:
        stories.extend(fetch_hn(q, MAX_PER_HN_QUERY))

    # Dedupe within this batch, drop already-seen.
    uniq, batch_ids = [], set()
    for s in stories:
        if s["id"] in seen or s["id"] in batch_ids:
            continue
        batch_ids.add(s["id"])
        uniq.append(s)

    curated = [s for s in load_override() if s["id"] not in seen]
    final = curated + uniq
    # Fetch full article text so the writer works from substance, not
    # headlines (thin sources are what got the fact-check veto in run #5).
    # HN stories carry direct publisher URLs; Google News redirect links
    # can't be fetched reliably and are skipped.
    for s in final[:12]:
        if not s.get("article"):
            s["article"] = fetch_article(s.get("url", ""))
    out = OUT_DIR / "stories.json"
    out.write_text(json.dumps(final[:12], indent=2))
    n_art = sum(1 for s in final[:12] if s.get("article"))
    print(f"[scout] {len(curated)} curated + {len(uniq)} fresh "
          f"({n_art} with article text) -> {out}")


if __name__ == "__main__":
    main()
