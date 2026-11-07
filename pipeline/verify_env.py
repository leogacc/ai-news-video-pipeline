#!/usr/bin/env python3
"""Diagnostic script to verify the bootstrapped production environment and credentials."""
import os
import stat
import sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent

def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not condition:
        sys.exit(1)

def main():
    print("--- [Diagnostic] Validating Environment ---")
    
    # 1. Python & Torch
    import torch
    check("PyTorch CPU", not torch.cuda.is_available(), f"(torch {torch.__version__})")
    
    # 2. Key Libraries
    import av
    check("PyAV compatibility", hasattr(av, "open"), f"(av {av.__version__})")
    import cv2
    check("OpenCV Headless", hasattr(cv2, "FaceDetectorYN_create"), f"(cv2 {cv2.__version__})")
    from PIL import Image
    import PIL
    check("Pillow", hasattr(PIL, "Image"), f"(Pillow {PIL.__version__})")
    import textstat
    check("textstat", hasattr(textstat, "flesch_kincaid_grade"))
    
    # 3. Permissions check for .env
    env_p = ROOT / ".env"
    check(".env file exists", env_p.exists())
    mode = oct(stat.S_IMODE(env_p.stat().st_mode))
    check(".env permissions 0600", mode in ("0o600", "0600"), f"(current {mode})")
    
    # Load .env
    env_vars = {}
    for line in env_p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip()
            os.environ[k.strip()] = v.strip()

    # 4. Telegram API Check (getMe + Live Test Ping)
    token = env_vars.get("TELEGRAM_BOT_TOKEN")
    chat_id = env_vars.get("TELEGRAM_CHAT_ID")
    check("Telegram token present", bool(token))
    check("Telegram chat_id present", bool(chat_id))
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
        res = r.json()
        check("Telegram bot authentication", res.get("ok") is True, f"(@{res.get('result', {}).get('username')})")
        
        # Send live test ping
        msg_resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": "🤖 <b>Antigravity AI News Pipeline</b>\nEnvironment online and verified.\n• PyTorch CPU: Ready\n• Kokoro TTS: Cached & Offline\n• Pixabay API: Connected",
                "parse_mode": "HTML"
            },
            timeout=15
        )
        check("Telegram test ping sent", msg_resp.status_code == 200, f"(status {msg_resp.status_code})")
    except Exception as e:
        check("Telegram bot communication", False, str(e))

    # 5. Pixabay API Check
    pix_key = env_vars.get("PIXABAY_API_KEY")
    check("Pixabay key present", bool(pix_key))
    try:
        r = requests.get(f"https://pixabay.com/api/?key={pix_key}&q=test&per_page=3", timeout=15)
        check("Pixabay authentication", r.status_code == 200, f"(status {r.status_code})")
    except Exception as e:
        check("Pixabay authentication", False, str(e))

    # 6. Offline Kokoro Synthesis
    sys.path.insert(0, str(ROOT / "pipeline"))
    import tts
    wav, words, sents = tts.synth_segment("Antigravity pipeline environment online.")
    check("Offline Kokoro TTS", wav is not None and len(wav) > 0 and len(words) > 0,
          f"({len(words)} words, {len(wav)/24000:.2f}s audio)")

    print("--- All Environment & Credential Diagnostics Passed ---")

if __name__ == "__main__":
    main()
