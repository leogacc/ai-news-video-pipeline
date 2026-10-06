#!/usr/bin/env python3
"""PUBLISHER.

Phase 1 (day one): Telegram review queue — video + title + hashtags land in
your chat; you post from your phone in ~30s per platform. Zero approvals needed.
Phase 2: YouTube Data API upload (starts private until Google OAuth verification
passes; native publishAt scheduling).
Phase 3: IG Reels + TikTok adapters (need Meta app review / TikTok audit first).

Dedupe rule: story ids are only marked posted after a successful publish, and
the Telegram caption carries the story id so a retry can never double-post.
"""
import base64
import json
import os
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text())


def telegram_send(video: Path, caption: str):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = os.environ["TELEGRAM_CHAT_ID"]
    with open(video, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideo",
            data={"chat_id": chat, "caption": caption[:1024],
                  "parse_mode": "HTML"},
            files={"video": (video.name, f, "video/mp4")},
            timeout=300)
    r.raise_for_status()
    print("[publish] sent to Telegram review queue")


def youtube_upload(video: Path, title: str, description: str, tags: list,
                   publish_at: str | None = None):
    """Needs YOUTUBE_CLIENT_SECRETS (OAuth client JSON, base64) and a prior
    local auth to mint token.json. Uploads as private until Google verifies
    the OAuth app — by design."""
    import pickle
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_p = ROOT / "token.pickle"
    creds = None
    if token_p.exists():
        creds = pickle.loads(token_p.read_bytes())
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
        else:
            secrets = json.loads(base64.b64decode(os.environ["YOUTUBE_CLIENT_SECRETS"]))
            (ROOT / "client_secrets.json").write_text(json.dumps(secrets))
            flow = InstalledAppFlow.from_client_secrets_file(
                str(ROOT / "client_secrets.json"),
                ["https://www.googleapis.com/auth/youtube.upload"])
            creds = flow.run_local_server(port=0)
        token_p.write_bytes(pickle.dumps(creds))

    yt = build("youtube", "v3", credentials=creds)
    status = {"privacyStatus": CFG["publish"]["youtube_privacy"]}
    if publish_at:
        status["publishAt"] = publish_at  # native scheduling — YT only
    body = {"snippet": {"title": title[:100], "description": description,
                        "tags": tags, "categoryId": "28"},  # Science & Technology
            "status": status}
    req = yt.videos().insert(part="snippet,status",
                             body=body,
                             media_body=MediaFileUpload(str(video), resumable=True))
    resp = req.execute()
    print(f"[publish] YouTube upload -> video id {resp['id']}")
    return resp["id"]


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    video = ROOT / "output" / f"ainews_{mode}.mp4"
    script = json.loads((ROOT / "output" / "script.json").read_text())
    tags = script.get("hashtags", [])
    caption = (f"<b>{script['title']}</b>\n\n{' '.join(tags)}\n\n"
               f"story_ids: {','.join(script.get('story_ids', []))}")

    publish_mode = os.environ.get("PUBLISH_MODE", CFG["publish"]["mode"])
    yt_id = None
    if publish_mode in ("telegram_queue", "all"):
        telegram_send(video, caption)
    if publish_mode in ("youtube", "all"):
        yt_id = youtube_upload(
            video, script["title"],
            script.get("description", "") + "\n\nSources:\n" + "\n".join(
                f"- {s['title']}: {s['url']}" for s in script.get("sources", [])),
            [t.lstrip("#") for t in tags])

    # Mark posted ONLY after successful publish.
    state_p = ROOT / "state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    posted = set(state.get("posted_ids", []))
    posted.update(script.get("story_ids", []))
    state["posted_ids"] = sorted(posted)
    state["seen_ids"] = sorted(set(state.get("seen_ids", [])) | posted)
    if yt_id:
        state.setdefault("youtube_ids", {})[video.name] = yt_id
    state_p.write_text(json.dumps(state, indent=2))
    print("[publish] state updated")


if __name__ == "__main__":
    main()
