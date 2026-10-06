#!/usr/bin/env python3
"""Orchestrator — runs every stage in order. Any exception aborts the run and
sends a Telegram alert. Nothing partial ever publishes (see qa.py + the
state-update rule in publish.py).
"""
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent

STAGES = ["ingest", "write", "tts", "captions", "visuals", "render", "qa", "publish"]


def alert(msg: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[run] no Telegram credentials — alert not sent")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat, "text": f"🚨 pipeline failed\n{msg}"[:4000]},
            timeout=30)
    except Exception as e:
        print(f"[run] alert failed: {e}")


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    env = dict(os.environ)
    try:
        for stage in STAGES:
            print(f"\n===== STAGE: {stage} ({mode}) =====")
            subprocess.run([sys.executable, str(ROOT / f"{stage}.py"),
                            "--mode", mode],
                           check=True, env=env, cwd=str(ROOT))
        print(f"\n[run] {mode} pipeline complete")
    except subprocess.CalledProcessError as e:
        tb = traceback.format_exc(limit=5)
        alert(f"stage failed: {e.cmd[0] if e.cmd else '?'}\n{tb[-1500:]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
