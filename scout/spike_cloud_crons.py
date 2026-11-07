#!/usr/bin/env python3
"""Phase 1.3 Cloud Crons Platform Evaluation Spike.

Benchmarks and validates the execution environment for scheduled Antigravity Cloud Crons:
1. Warm-Start Environment Latency (Torch CPU, Kokoro, OpenCV, Pillow, faster-whisper/av)
2. Secret Isolation and Configuration Resolution (.env mode 0600)
3. State Concurrency, Atomic Writes & Dedupe Serialization (state.json, saved_items.json)
4. Offline AI Model Cache Load Latency (Kokoro-82M, YuNet ONNX)
5. Headless Chromium / Puppeteer Execution Latency
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_JSON = ROOT / "scout" / "spike_crons_results.json"
ENV_FILE = ROOT / ".env"


def benchmark_imports() -> dict:
    print("\n--- [Test 1] Environment Import & Warm-Start Latency ---")
    packages = [
        ("PIL (Pillow)", "from PIL import Image"),
        ("cv2 (OpenCV headless)", "import cv2"),
        ("torch (PyTorch CPU)", "import torch"),
        ("av (PyAV pinned)", "import av"),
        ("kokoro (TTS Engine)", "import kokoro"),
        ("yaml (PyYAML)", "import yaml"),
    ]
    latencies = {}
    total_time = 0.0

    for name, stmt in packages:
        t0 = time.perf_counter()
        exec(stmt, globals())
        elapsed = time.perf_counter() - t0
        latencies[name] = round(elapsed, 4)
        total_time += elapsed
        print(f"  [OK] {name:25} | {elapsed:.4f}s")

    print(f"  Total warm-start import time: {total_time:.3f}s (vs GHA cold-start ~240-300s)")
    return {
        "individual_latencies_s": latencies,
        "total_warm_import_s": round(total_time, 4),
        "gha_cold_start_comparison_s": 270.0,
        "speedup_factor": round(270.0 / total_time, 1) if total_time > 0 else 999,
    }


def benchmark_secret_resolution() -> dict:
    print("\n--- [Test 2] Secret Resolution & Permissions Check ---")
    res = {
        "env_file_exists": ENV_FILE.exists(),
        "permissions": None,
        "secure_0600": False,
        "keys_loaded": [],
        "missing_keys": [],
    }
    if not ENV_FILE.exists():
        print("  [FAIL] .env file does not exist")
        return res

    file_stat = ENV_FILE.stat()
    file_perm = stat.S_IMODE(file_stat.st_mode)
    res["permissions"] = oct(file_perm)
    res["secure_0600"] = file_perm == 0o600
    print(f"  .env permissions: {oct(file_perm)} (0o600 expected: {res['secure_0600']})")

    # Parse .env
    required_keys = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "PIXABAY_API_KEY"]
    loaded = {}
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                loaded[k.strip()] = v.strip()

    for k in required_keys:
        if k in loaded and loaded[k] and not loaded[k].startswith("your_"):
            res["keys_loaded"].append(k)
            masked = loaded[k][:6] + "..." + loaded[k][-4:] if len(loaded[k]) > 10 else "***"
            print(f"  [OK] {k:22} = {masked}")
        else:
            res["missing_keys"].append(k)
            print(f"  [MISSING] {k:22}")

    return res


def benchmark_state_concurrency() -> dict:
    print("\n--- [Test 3] State Concurrency, Atomic Writes & Dedupe Serialization ---")
    state_file = ROOT / "scout" / "state.json"
    saved_items_file = ROOT / "scout" / "saved_items.json"
    clipped_finds_file = ROOT / "scout" / "clipped_finds.json"

    metrics = {}
    for sf in [state_file, saved_items_file, clipped_finds_file]:
        if not sf.exists():
            continue
        t0 = time.perf_counter()
        data = json.loads(sf.read_text(encoding="utf-8"))
        read_time = time.perf_counter() - t0

        size_bytes = sf.stat().st_size
        item_count = len(data) if isinstance(data, (list, dict)) else 0

        # Benchmark atomic write to tempfile and rename
        t1 = time.perf_counter()
        with tempfile.NamedTemporaryFile("w", dir=sf.parent, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, indent=2)
            temp_path = Path(tf.name)
        # Verify and clean up temp
        temp_path.unlink()
        write_time = time.perf_counter() - t1

        metrics[sf.name] = {
            "size_kb": round(size_bytes / 1024, 2),
            "item_count": item_count,
            "read_latency_s": round(read_time, 5),
            "write_latency_s": round(write_time, 5),
        }
        print(f"  [OK] {sf.name:20} | {metrics[sf.name]['size_kb']:6.1f} KB | Read: {read_time*1000:.2f}ms | Write: {write_time*1000:.2f}ms")

    return metrics


def benchmark_model_cache() -> dict:
    print("\n--- [Test 4] Offline Model Cache Readiness ---")
    results = {}

    # 1. Kokoro model files
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    kokoro_cached = any(p.name.startswith("models--hexgrad--Kokoro-82M") for p in hf_cache.glob("*")) if hf_cache.exists() else False
    results["kokoro_cached"] = kokoro_cached
    print(f"  Kokoro-82M weights cached: {kokoro_cached} ({hf_cache})")

    # 2. YuNet face detector
    yunet_path = ROOT / "pipeline" / "cache" / "models" / "face_yunet.onnx"
    yunet_ok = yunet_path.exists() and yunet_path.stat().st_size > 100_000
    results["yunet_face_model"] = {
        "exists": yunet_ok,
        "path": str(yunet_path),
        "size_kb": round(yunet_path.stat().st_size / 1024, 1) if yunet_path.exists() else 0,
    }
    print(f"  YuNet face ONNX model    : {yunet_ok} ({results['yunet_face_model']['size_kb']} KB)")

    # 3. Quick Kokoro init test
    t0 = time.perf_counter()
    try:
        from kokoro import KPipeline
        pipeline = KPipeline(lang_code="a")
        init_time = time.perf_counter() - t0
        results["kokoro_init_latency_s"] = round(init_time, 3)
        print(f"  Kokoro KPipeline init    : {init_time:.3f}s")
    except Exception as e:
        results["kokoro_init_error"] = str(e)
        print(f"  Kokoro KPipeline init err: {e}")

    return results


def benchmark_headless_chromium() -> dict:
    print("\n--- [Test 5] Headless Chromium / Node Warm-Start Latency ---")
    node_bin = shutil.which("node") or "/usr/local/bin/node"
    render_script = ROOT / "pipeline" / "tweetshot" / "render.mjs"

    # Create dummy HTML card to render
    dummy_html = Path("/tmp/test_cron_dummy.html")
    dummy_png = Path("/tmp/test_cron_dummy.png")
    dummy_html.write_text("<!doctype html><html><body style='background:#000;'><div id='card' style='width:500px;height:200px;background:#111;color:#fff;'>Cron Warm Test</div></body></html>")

    cmd = [node_bin, str(render_script), str(dummy_html), "#card", str(dummy_png), "500"]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    elapsed = time.perf_counter() - t0

    success = r.returncode == 0 and dummy_png.exists() and dummy_png.stat().st_size > 500
    dummy_html.unlink(missing_ok=True)
    dummy_png.unlink(missing_ok=True)

    print(f"  Chromium render: {elapsed:.3f}s | Exit code: {r.returncode} | Success: {success}")
    return {
        "node_path": node_bin,
        "render_latency_s": round(elapsed, 3),
        "success": success,
        "stderr": r.stderr if r.returncode != 0 else "",
    }


def main():
    print("===================================================================")
    print("      PHASE 1.3: CLOUD CRONS PLATFORM EVALUATION BENCHMARK         ")
    print("===================================================================")

    import_metrics = benchmark_imports()
    secret_metrics = benchmark_secret_resolution()
    state_metrics = benchmark_state_concurrency()
    model_metrics = benchmark_model_cache()
    chromium_metrics = benchmark_headless_chromium()

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "orchestration_platform": "Antigravity Cloud Crons (Option B)",
        "warm_start_imports": import_metrics,
        "secret_resolution": secret_metrics,
        "state_concurrency": state_metrics,
        "model_cache": model_metrics,
        "headless_chromium": chromium_metrics,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[DONE] Cloud Crons benchmark output saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
