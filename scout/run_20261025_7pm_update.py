#!/usr/bin/env python3
"""7pm scout run (2026-10-25) state update — run after browser X check returns.
Appends newly classified items to scout/saved_items.json and updates scout/state.json.
"""
import json, os

BASE = os.path.expanduser("~/workspace/ai-video-pipeline/scout")
SAVED = os.path.join(BASE, "saved_items.json")
STATE = os.path.join(BASE, "state.json")

saved = json.load(open(SAVED))
state = json.load(open(STATE))
existing_ids = {it["post_id"] for it in saved}

new_items = [
    {
        "post_id": "2114461632512274812",
        "author": "kimmonismus",
        "date": "2026-10-25",
        "text": "Apologizing for poor rates, but failing to apologize for the fact that influencer briefings were sent out requesting undisclosed paid promotions, is a brazen move. Not cool Kimi!",
        "url": "https://x.com/kimmonismus/status/2114461632512274812",
        "category": "release",
        "source": "account:kimmonismus (Kimi K3.1 Pro apology + one-time usage reset relayed; corroborated by matching Threads post De7t4-2jvEo)",
        "verified_link": "",
        "notes": "Company announcement relayed by the scout account (same precedent as Nanbeige4.3 release). Not a find — no tool/demo — so not a clip candidate.",
    },
    {
        "post_id": "threads:De7t4-2jvEo",
        "author": "kimmonismus",
        "date": "2026-10-25",
        "text": "Kimi (Moonshot AI) just apologized for the rate limits and quota problems on its K3.1 Pro plan and is giving every subscriber a one-time usage reset. Apologizing for poor rates, but failing to apologize for the fact that influencer briefings were sent out requesting undisclosed paid promotions, is a brazen move. Not cool Kimi!",
        "url": "https://www.threads.com/@kimmonismus/post/De7t4-2jvEo",
        "category": "release",
        "source": "threads:kimmonismus (MIRROR of X post 2114461632512274812 — same author, story, day, near-identical text; coverage only, never a pick)",
        "verified_link": "",
    },
    {
        "post_id": "threads:De7ma_ODm99",
        "author": "kimmonismus",
        "date": "2026-10-25",
        "text": "Quick reminder: Anthropic is planning its IPO for around November 9th. That makes it very likely they'll release Fable 5.5 next week to maximize the valuation right before going public. OpenAI, of course, won't be far behind and will counter, although right now only Terra 6.1 is rumored. So yeah, next week could be pretty significant.",
        "url": "https://www.threads.com/@kimmonismus/post/De7ma_ODm99",
        "category": "rumor",
        "source": "threads:kimmonismus (MIRROR of already-saved X rumor 2114451669811372151 — coverage only, never a pick)",
        "verified_link": "",
    },
]

for it in new_items:
    if it["post_id"] not in existing_ids:
        saved.append(it)
        existing_ids.add(it["post_id"])
        print("appended", it["post_id"])
    else:
        print("already present", it["post_id"])

json.dump(saved, open(SAVED, "w"), indent=2, ensure_ascii=False)
print("saved_items total:", len(saved))

# state updates
seen = set(state.get("seen_post_ids", []))
for pid in ["2114461632512274812", "2114385976675987946", "2114319575512760669",
            "2114424160675885422", "2110724880085696735"]:
    seen.add(pid)
state["seen_post_ids"] = sorted(seen)
threads_seen = set(state.get("seen_threads_urls", []))
for url in [
    "https://www.threads.com/@kimmonismus/post/DehF7_ejj3X",
    "https://www.threads.com/@kimmonismus/post/DehGAfTjp2_",
    "https://www.threads.com/@kimmonismus/post/De7t4-2jvEo",
    "https://www.threads.com/@kimmonismus/post/De7ma_ODm99",
    "https://www.threads.com/@kimmonismus/post/De7miFaDsq3",
    "https://www.threads.com/@kimmonismus/post/De7Z2d8jnm3",
    "https://www.threads.com/@kimmonismus/post/De7SgIqjoAb",
    "https://www.threads.com/@kimmonismus/post/De7ZpWTDg8V",
]:
    threads_seen.add(url)
state["seen_threads_urls"] = sorted(threads_seen)
state["last_scout_run"] = "2026-10-25T19:00:00-0700"
json.dump(state, open(STATE, "w"), indent=2)
print("state updated; seen_post_ids:", len(state["seen_post_ids"]),
      "seen_threads_urls:", len(state["seen_threads_urls"]))
