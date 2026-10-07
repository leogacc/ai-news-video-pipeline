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


def reading_level_only() -> bool:
    """True if QA's only blocking failure was the reading-level gate."""
    try:
        rep = json.loads((ROOT / "output" / "qa.json").read_text())
    except Exception:
        return False
    return rep.get("failures") == ["reading level <= 9.5"]


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    env = dict(os.environ)
    simplify_tries = 0
    i = 0
    try:
        while i < len(STAGES):
            stage = STAGES[i]
            print(f"\n===== STAGE: {stage} ({mode}) =====")
            try:
                subprocess.run([sys.executable, str(ROOT / f"{stage}.py"),
                                "--mode", mode],
                               check=True, env=env, cwd=str(ROOT))
            except subprocess.CalledProcessError:
                # QA blocked only on reading level -> rewrite the script in
                # simpler language and redo write..qa (max 2 tries). The
                # video was already fully built once; this just dumbs down
                # the wording until the high-school gate passes.
                if stage == "qa" and simplify_tries < 2 and reading_level_only():
                    simplify_tries += 1
                    print(f"[run] QA blocked only on reading level — "
                          f"simplifying script (try {simplify_tries}/2)")
                    env["SIMPLIFY"] = "1"
                    i = STAGES.index("write")
                    continue
                raise
            i += 1
        print(f"\n[run] {mode} pipeline complete")
    except subprocess.CalledProcessError as e:
        tb = traceback.format_exc(limit=5)
        alert(f"stage failed: {e.cmd[0] if e.cmd else '?'}\n{tb[-1500:]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
