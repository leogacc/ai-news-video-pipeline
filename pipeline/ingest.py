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
import urllib.parse
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

MAX_PER_QUERY = 8


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

    # Dedupe within this batch, drop already-seen.
    uniq, batch_ids = [], set()
    for s in stories:
        if s["id"] in seen or s["id"] in batch_ids:
            continue
        batch_ids.add(s["id"])
        uniq.append(s)

    curated = [s for s in load_override() if s["id"] not in seen]
    final = curated + uniq
    out = OUT_DIR / "stories.json"
    out.write_text(json.dumps(final[:12], indent=2))
    print(f"[scout] {len(curated)} curated + {len(uniq)} fresh -> {out}")


if __name__ == "__main__":
    main()
