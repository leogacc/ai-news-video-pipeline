#!/usr/bin/env python3
"""Phase 1.2 Free X Search Spike Benchmark Suite.

Tests and compares free, unauthenticated X search, ingestion, and media extraction
methods to decommission Threads and establish a reliable free X pipeline:
1. VIP Account Monitoring: Syndication Profile vs fxtwitter vs Nitter
2. Keyword Search: Google News RSS (site:x.com) vs HN Algolia
3. Media Fidelity: Video MP4 variants, photo resolutions, engagement stats
4. Burst Resilience: Rate limit stress test (30 rapid queries)
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS_FILE = ROOT / "scout" / "accounts.yaml"
OUTPUT_JSON = ROOT / "scout" / "spike_results.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def http_get(url: str, timeout: int = 15, headers: dict = None) -> tuple[int, bytes, float]:
    """Perform HTTP GET returning (status_code, body, elapsed_seconds)."""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed = time.perf_counter() - t0
            return resp.status, body, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - t0
        return e.code, e.read() if hasattr(e, "read") else b"", elapsed
    except Exception as e:
        elapsed = time.perf_counter() - t0
        return 0, str(e).encode(), elapsed


def test_syndication_timeline(handles: list[str]) -> dict:
    print(f"\n--- [Test 1A] Official Twitter Syndication Timeline ({len(handles)} accounts) ---")
    results = {}
    total_time = 0.0
    success_count = 0

    for h in handles:
        url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{h}"
        status, body, elapsed = http_get(url, timeout=12)
        total_time += elapsed
        res = {
            "status": status,
            "latency_s": round(elapsed, 3),
            "tweet_count": 0,
            "latest_tweet": None,
            "verified": False,
            "user_name": None,
            "error": None,
        }
        if status == 200:
            try:
                html_text = body.decode("utf-8", errors="replace")
                m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_text)
                if m:
                    data = json.loads(m.group(1))
                    tl = data.get("props", {}).get("pageProps", {}).get("timeline", {})
                    entries = tl.get("entries") or []
                    res["tweet_count"] = len(entries)
                    if entries:
                        first_tw = entries[0].get("content", {}).get("tweet", {})
                        u = first_tw.get("user", {})
                        res["user_name"] = u.get("name")
                        res["verified"] = u.get("is_blue_verified") or u.get("verified") or False
                        res["latest_tweet"] = {
                            "id": first_tw.get("id_str"),
                            "created_at": first_tw.get("created_at"),
                            "text": (first_tw.get("full_text") or first_tw.get("text") or "")[:120],
                            "likes": first_tw.get("favorite_count", 0),
                            "retweets": first_tw.get("retweet_count", 0),
                            "has_media": bool(first_tw.get("entities", {}).get("media")),
                        }
                    success_count += 1
                    print(f"  [OK] @{h:16} | {elapsed:.2f}s | {res['tweet_count']:3} tweets | Latest: {res['latest_tweet']['id'] if res['latest_tweet'] else 'none'}")
                else:
                    res["error"] = "No __NEXT_DATA__ in HTML"
                    print(f"  [FAIL] @{h:14} | {elapsed:.2f}s | {res['error']}")
            except Exception as e:
                res["error"] = str(e)
                print(f"  [ERR] @{h:15} | {elapsed:.2f}s | {e}")
        else:
            res["error"] = f"HTTP {status}"
            print(f"  [HTTP {status}] @{h:10} | {elapsed:.2f}s")
        results[h] = res
        time.sleep(0.1)  # polite spacing

    avg_latency = round(total_time / len(handles), 3) if handles else 0
    return {
        "success_rate": f"{success_count}/{len(handles)} ({round(success_count/len(handles)*100, 1)}%)",
        "avg_latency_s": avg_latency,
        "accounts": results,
    }


def test_fxtwitter_profile(handles: list[str]) -> dict:
    print(f"\n--- [Test 1B] fxtwitter Profile API Sample ({len(handles)} accounts) ---")
    results = {}
    success_count = 0
    total_time = 0.0

    for h in handles:
        url = f"https://api.fxtwitter.com/{h}"
        status, body, elapsed = http_get(url, timeout=10)
        total_time += elapsed
        res = {
            "status": status,
            "latency_s": round(elapsed, 3),
            "error": None,
        }
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8"))
                user = data.get("user") or {}
                res["user_name"] = user.get("name")
                res["tweets"] = len(user.get("tweets") or [])
                success_count += 1
                print(f"  [OK] @{h:16} | {elapsed:.2f}s | User: {res['user_name']}")
            except Exception as e:
                res["error"] = str(e)
                print(f"  [ERR] @{h:15} | {elapsed:.2f}s | {e}")
        else:
            res["error"] = f"HTTP {status}"
            print(f"  [HTTP {status}] @{h:10} | {elapsed:.2f}s")
        results[h] = res
        time.sleep(0.2)

    return {
        "success_rate": f"{success_count}/{len(handles)} ({round(success_count/len(handles)*100, 1)}%)",
        "avg_latency_s": round(total_time / len(handles), 3) if handles else 0,
        "accounts": results,
    }


def test_nitter_instances(handles: list[str]) -> dict:
    print(f"\n--- [Test 1C] Public Nitter Instance Viability ---")
    instances = [
        "https://nitter.net",
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
        "https://nitter.cz",
        "https://lightbrd.com",
    ]
    results = {}
    test_handle = handles[0] if handles else "OpenAI"

    for inst in instances:
        url = f"{inst}/{test_handle}/rss"
        status, body, elapsed = http_get(url, timeout=8)
        alive = status == 200 and b"<rss" in body
        results[inst] = {
            "status": status,
            "latency_s": round(elapsed, 3),
            "alive": alive,
            "error": None if alive else f"HTTP {status} or invalid RSS",
        }
        status_label = "ALIVE" if alive else f"DEAD (HTTP {status})"
        print(f"  [{status_label}] {inst:32} | {elapsed:.2f}s")

    return results


def test_google_news_rss(queries: list[str]) -> dict:
    print(f"\n--- [Test 2A] Google News RSS site:x.com Search ({len(queries)} queries) ---")
    results = {}
    total_time = 0.0
    total_tweets_found = 0

    for q in queries:
        encoded_q = urllib.parse.quote(f"site:x.com {q}")
        url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"
        status, body, elapsed = http_get(url, timeout=12)
        total_time += elapsed
        res = {
            "status": status,
            "latency_s": round(elapsed, 3),
            "items_count": 0,
            "items": [],
            "error": None,
        }
        if status == 200:
            try:
                root = ET.fromstring(body)
                items = root.findall(".//item")
                res["items_count"] = len(items)
                total_tweets_found += len(items)
                for it in items[:3]:
                    title = it.findtext("title", "")
                    link = it.findtext("link", "")
                    pub_date = it.findtext("pubDate", "")
                    source = it.findtext("source", "")
                    res["items"].append({
                        "title": title[:100],
                        "link": link[:90],
                        "pub_date": pub_date,
                        "source": source,
                    })
                print(f"  [OK] '{q[:20]:20}' | {elapsed:.2f}s | {len(items):3} results | Top: {res['items'][0]['title'][:50] if res['items'] else 'none'}")
            except Exception as e:
                res["error"] = str(e)
                print(f"  [ERR] '{q[:20]:20}' | {elapsed:.2f}s | {e}")
        else:
            res["error"] = f"HTTP {status}"
            print(f"  [HTTP {status}] '{q[:20]:20}' | {elapsed:.2f}s")
        results[q] = res
        time.sleep(0.1)

    return {
        "total_queries": len(queries),
        "total_results": total_tweets_found,
        "avg_latency_s": round(total_time / len(queries), 3) if queries else 0,
        "queries": results,
    }


def test_hn_algolia_search(queries: list[str]) -> dict:
    print(f"\n--- [Test 2B] Hacker News Algolia Search for AI Dispatches ({len(queries)} queries) ---")
    results = {}
    total_time = 0.0
    total_hits = 0

    for q in queries:
        encoded_q = urllib.parse.quote(q)
        url = f"https://hn.algolia.com/api/v1/search_by_date?query={encoded_q}&tags=story&hitsPerPage=10"
        status, body, elapsed = http_get(url, timeout=10)
        total_time += elapsed
        res = {
            "status": status,
            "latency_s": round(elapsed, 3),
            "hits_count": 0,
            "top_hits": [],
            "x_links_count": 0,
            "error": None,
        }
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8"))
                hits = data.get("hits", [])
                res["hits_count"] = len(hits)
                total_hits += len(hits)
                for h in hits:
                    url_val = h.get("url") or ""
                    is_x = "x.com" in url_val or "twitter.com" in url_val
                    if is_x:
                        res["x_links_count"] += 1
                    if len(res["top_hits"]) < 3:
                        res["top_hits"].append({
                            "title": h.get("title", "")[:90],
                            "points": h.get("points", 0),
                            "comments": h.get("num_comments", 0),
                            "url": url_val[:80],
                            "is_x_link": is_x,
                        })
                print(f"  [OK] '{q[:20]:20}' | {elapsed:.2f}s | {len(hits):2} hits | X links: {res['x_links_count']}")
            except Exception as e:
                res["error"] = str(e)
                print(f"  [ERR] '{q[:20]:20}' | {elapsed:.2f}s | {e}")
        else:
            res["error"] = f"HTTP {status}"
            print(f"  [HTTP {status}] '{q[:20]:20}' | {elapsed:.2f}s")
        results[q] = res
        time.sleep(0.1)

    return {
        "total_queries": len(queries),
        "total_hits": total_hits,
        "avg_latency_s": round(total_time / len(queries), 3) if queries else 0,
        "queries": results,
    }


def test_media_fidelity(test_cases: list[dict]) -> dict:
    print(f"\n--- [Test 3] Media & Video Extraction Fidelity ---")
    results = {}

    for tc in test_cases:
        sid = tc["id"]
        label = tc["label"]
        print(f"\n  Evaluating {label} (ID: {sid}):")

        # 1. Syndication CDN
        syn_url = f"https://cdn.syndication.twimg.com/tweet-result?id={sid}&token=x"
        status, body, elapsed = http_get(syn_url, timeout=10)
        syn_res = {"status": status, "latency_s": round(elapsed, 3)}
        if status == 200:
            try:
                data = json.loads(body.decode("utf-8"))
                media_list = data.get("mediaDetails") or []
                syn_res["media_count"] = len(media_list)
                syn_res["types"] = [m.get("type") for m in media_list]
                syn_res["photo_urls"] = [m.get("media_url_https") for m in media_list if m.get("type") == "photo"]
                
                # Check video info
                videos = []
                for m in media_list:
                    if m.get("type") == "video":
                        vinfo = m.get("video_info", {})
                        variants = vinfo.get("variants", [])
                        mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
                        # sort by bitrate
                        mp4s.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
                        videos.append({
                            "duration_ms": vinfo.get("duration_millis"),
                            "variants_count": len(variants),
                            "best_mp4": mp4s[0].get("url") if mp4s else None,
                            "best_bitrate": mp4s[0].get("bitrate") if mp4s else None,
                        })
                syn_res["videos"] = videos
                print(f"    Syndication CDN: {elapsed:.2f}s | Photos: {len(syn_res['photo_urls'])}, Videos: {len(videos)}")
                if videos and videos[0].get("best_mp4"):
                    print(f"      Best Video: {videos[0]['best_bitrate']} bps -> {videos[0]['best_mp4'][:70]}...")
            except Exception as e:
                syn_res["error"] = str(e)
                print(f"    Syndication CDN error: {e}")
        else:
            syn_res["error"] = f"HTTP {status}"
            print(f"    Syndication CDN HTTP {status}")

        # 2. fxtwitter API
        fx_url = f"https://api.fxtwitter.com/{tc['handle']}/status/{sid}"
        f_status, f_body, f_elapsed = http_get(fx_url, timeout=10)
        fx_res = {"status": f_status, "latency_s": round(f_elapsed, 3)}
        if f_status == 200:
            try:
                f_data = json.loads(f_body.decode("utf-8")).get("tweet", {})
                f_media = f_data.get("media") or {}
                fx_res["photos_count"] = len(f_media.get("photos") or [])
                fx_res["videos_count"] = len(f_media.get("videos") or [])
                f_vids = f_media.get("videos") or []
                if f_vids:
                    fx_res["best_video_url"] = f_vids[0].get("url")
                    fx_res["thumbnail_url"] = f_vids[0].get("thumbnail_url")
                print(f"    fxtwitter API  : {f_elapsed:.2f}s | Photos: {fx_res['photos_count']}, Videos: {fx_res['videos_count']}")
                if f_vids:
                    print(f"      Video URL: {f_vids[0].get('url', '')[:70]}...")
            except Exception as e:
                fx_res["error"] = str(e)
                print(f"    fxtwitter error: {e}")
        else:
            fx_res["error"] = f"HTTP {f_status}"
            print(f"    fxtwitter HTTP {f_status}")

        results[sid] = {
            "label": label,
            "handle": tc["handle"],
            "syndication": syn_res,
            "fxtwitter": fx_res,
        }

    return results


def test_burst_resilience() -> dict:
    print(f"\n--- [Test 4] Burst Resilience Stress Test (30 Rapid Queries) ---")
    total_queries = 30
    latencies = []
    status_codes = {}
    test_id = "1889059531625464090"  # Sam Altman tweet

    t_start = time.perf_counter()
    for i in range(total_queries):
        url = f"https://cdn.syndication.twimg.com/tweet-result?id={test_id}&token=x&burst={i}"
        status, _, elapsed = http_get(url, timeout=10)
        latencies.append(elapsed)
        status_codes[status] = status_codes.get(status, 0) + 1
        if (i + 1) % 10 == 0 or status != 200:
            print(f"  Progress: {i+1:2}/{total_queries} completed | HTTP {status} | latest latency: {elapsed:.2f}s")
    total_duration = time.perf_counter() - t_start

    avg_latency = round(sum(latencies) / len(latencies), 3)
    p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 3)
    print(f"  Summary: {total_queries} queries in {total_duration:.2f}s ({round(total_queries/total_duration, 1)} req/s)")
    print(f"  Avg Latency: {avg_latency}s | P95 Latency: {p95_latency}s | Codes: {status_codes}")

    return {
        "total_requests": total_queries,
        "total_duration_s": round(total_duration, 3),
        "requests_per_sec": round(total_queries / total_duration, 2),
        "avg_latency_s": avg_latency,
        "p95_latency_s": p95_latency,
        "status_distribution": status_codes,
    }


def main():
    print("===================================================================")
    print("      PHASE 1.2: FREE X SEARCH & INGESTION INVESTIGATION SPIKE      ")
    print("===================================================================")

    # 1. Load accounts
    handles = ["sama", "gdb", "OpenAI", "demishassabis", "ylecun", "elonmusk", "ArthurMensh"]
    if ACCOUNTS_FILE.exists():
        with open(ACCOUNTS_FILE, "r") as f:
            cfg = yaml.safe_load(f)
            loaded_handles = [a["handle"] for a in cfg.get("accounts", []) if a.get("handle")]
            if loaded_handles:
                handles = loaded_handles
    print(f"Loaded {len(handles)} VIP scout accounts: {', '.join(handles[:7])}...")

    # 2. VIP Timeline Benchmarks
    syndication_results = test_syndication_timeline(handles)
    fxtwitter_results = test_fxtwitter_profile(handles[:5])  # subset to avoid aggressive rate limiting
    nitter_results = test_nitter_instances(handles)

    # 3. Keyword Search Benchmarks
    search_queries = [
        "OpenAI",
        "Anthropic Claude",
        "DeepSeek",
        "Mistral",
        "Qwen",
        "AI reasoning model",
        "new model release",
    ]
    google_news_results = test_google_news_rss(search_queries)
    hn_algolia_results = test_hn_algolia_search(search_queries)

    # 4. Media & Video Extraction Fidelity Test
    # Test cases:
    # - Sam Altman (Text only / Quote)
    # - OpenAI GPT-6.1 (Photo / Image gallery)
    # - Chubby / AI Demo video tweet
    test_media_cases = [
        {"id": "1889059531625464090", "handle": "sama", "label": "Text-only / Quote"},
        {"id": "2114780711664398349", "handle": "OpenAI", "label": "Multi-Image Announcement"},
        {"id": "1894814890664964522", "handle": "kimmonismus", "label": "AI Video Demo"},
    ]
    media_results = test_media_fidelity(test_media_cases)

    # 5. Burst Resilience Test
    burst_results = test_burst_resilience()

    # 6. Aggregate Output
    final_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "syndication_timeline": syndication_results,
        "fxtwitter_profile": fxtwitter_results,
        "nitter_viability": nitter_results,
        "google_news_rss": google_news_results,
        "hn_algolia": hn_algolia_results,
        "media_fidelity": media_results,
        "burst_resilience": burst_results,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(final_report, f, indent=2)

    print(f"\n[DONE] Raw benchmark output saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
