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


def quarantine_video(mode: str):
    """Move a QA-failed render out of the publish path with its QA report.
    A quarantined video never reaches Telegram."""
    import datetime
    qdir = ROOT / "output" / "quarantine"
    qdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        rep = json.loads((ROOT / "output" / "qa.json").read_text())
    except Exception:
        rep = {"failures": ["unknown"]}
    video = ROOT / "output" / f"ainews_{mode}.mp4"
    if video.exists():
        dest = qdir / f"ainews_{mode}_{stamp}.mp4"
        video.rename(dest)
        print(f"[run] quarantined -> {dest.name}")
    (qdir / f"qa_{mode}_{stamp}.json").write_text(json.dumps({
        "mode": mode, "quarantined_at": stamp,
        "failures": rep.get("failures", [])}, indent=2))


def quarantine_retry_bans() -> set:
    """Slugs of the stock clips used in the failed render, so the retry
    fetches different footage."""
    try:
        vs = json.loads((ROOT / "output" / "visuals.json").read_text())
    except Exception:
        return set()
    return {Path(v["path"]).stem
            for v in vs
            if v.get("source") in ("pixabay", "pexels", "cache",
                                   "clip-library")}
    """True if QA's only blocking failure was the reading-level gate."""
    try:
        rep = json.loads((ROOT / "output" / "qa.json").read_text())
    except Exception:
        return False
    return rep.get("failures") == ["reading level <= 9.5"]


def _start_run_log(mode):
    """Tee the whole run (this process + every stage subprocess) into a dated
    log file while keeping live console output. This is where the strategic
    [shot]/[resolve]/[crop] trace lines land for later debugging
    (user rule 2026-10-11: leave strategic logs so the pipeline is traceable).
    Returns a handle for _stop_run_log, or None if logging could not start
    (non-fatal — the run proceeds without it)."""
    import datetime
    try:
        logdir = ROOT / "logs"
        logdir.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = logdir / f"render-{mode}-{stamp}.log"
        # Prune: keep the 14 most recent run logs.
        for old in sorted(logdir.glob("render-*.log"))[:-13]:
            old.unlink(missing_ok=True)
        # tee must be spawned BEFORE dup2 so its own stdout still points at
        # the real console. FD-level redirect (not sys.stdout reassignment)
        # is what captures the child stage processes too.
        tee = subprocess.Popen(["tee", str(path)], stdin=subprocess.PIPE)
        saved = (os.dup(1), os.dup(2))
        os.dup2(tee.stdin.fileno(), 1)
        os.dup2(tee.stdin.fileno(), 2)
        print(f"[run] trace log -> {path}", flush=True)
        return (tee, saved, path)
    except Exception as e:
        print(f"[run] run-log disabled ({e})", flush=True)
        return None


def _stop_run_log(handle):
    if not handle:
        return
    tee, (saved_out, saved_err), path = handle
    try:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        tee.stdin.close()
        tee.wait(timeout=10)
    except Exception:
        pass
    finally:
        os.close(saved_out)
        os.close(saved_err)
    print(f"[run] trace log saved -> {path}", flush=True)


def _pipeline_version():
    """Read pipeline/VERSION (2026-10-12: every upgrade bumps it, so any
    video can be traced to the exact code that built it)."""
    try:
        return (ROOT / "VERSION").read_text().strip().split()[0]
    except Exception:
        return "unknown"


def _stamp_version():
    """Stamp the pipeline version into qa.json after the qa stage."""
    try:
        p = ROOT / "output" / "qa.json"
        rep = json.loads(p.read_text())
        rep["pipeline_version"] = _pipeline_version()
        p.write_text(json.dumps(rep, indent=2))
        print(f"[run] stamped pipeline version {rep['pipeline_version']} "
              f"into qa.json", flush=True)
    except Exception as e:
        print(f"[run] version stamp skipped ({e})", flush=True)


def main():
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "daily"
    skip = sys.argv[sys.argv.index("--skip") + 1].split(",") if "--skip" in sys.argv else []
    run_log = _start_run_log(mode)
    import atexit
    atexit.register(_stop_run_log, run_log)
    print(f"[run] pipeline version {_pipeline_version()}", flush=True)
    # On the VM branch the scheduled worker curates and writes the script
    # itself (it IS the scout/writer/fact-checker), so ingest+write are
    # skipped and the SIMPLIFY rewrite loop is disabled — the worker
    # rewrites in plain language directly if QA flags reading level.
    vm_write = "write" in skip
    env = dict(os.environ)
    simplify_tries = 0
    quarantine_retried = False
    i = 0
    try:
        while i < len(STAGES):
            stage = STAGES[i]
            if stage in skip:
                print(f"\n===== STAGE: {stage} ({mode}) — skipped (provided by worker) =====")
                i += 1
                continue
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
                if stage == "qa" and simplify_tries < 2 and reading_level_only() and not vm_write:
                    simplify_tries += 1
                    print(f"[run] QA blocked only on reading level — "
                          f"simplifying script (try {simplify_tries}/2)")
                    env["SIMPLIFY"] = "1"
                    i = STAGES.index("write")
                    continue
                # QA quarantine (2026-10-09): one automatic retry with
                # different clips before the video is quarantined.
                if stage == "qa" and not quarantine_retried:
                    quarantine_retried = True
                    bans = quarantine_retry_bans()
                    env["VISUALS_BAN"] = ",".join(sorted(bans))
                    env["VISUALS_RETRY"] = "1"
                    try:
                        fails = json.loads(
                            (ROOT / "output" / "qa.json").read_text()
                        ).get("failures", [])
                    except Exception:
                        fails = ["unknown"]
                    print(f"[run] QA failed {fails} — quarantine retry: "
                          f"re-running visuals/render/qa with "
                          f"{len(bans)} banned clips")
                    i = STAGES.index("visuals")
                    continue
                if stage == "qa":
                    quarantine_video(mode)
                raise
            if stage == "qa":
                _stamp_version()
            i += 1
        print(f"\n[run] {mode} pipeline complete")
    except subprocess.CalledProcessError as e:
        tb = traceback.format_exc(limit=5)
        alert(f"stage failed: {e.cmd[0] if e.cmd else '?'}\n{tb[-1500:]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
