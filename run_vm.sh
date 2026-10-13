#!/bin/bash
# VM-branch runner for the AI news video pipeline.
# The scheduled worker (Muse) curates stories and writes pipeline/output/script.json
# itself; this script runs the mechanical stages (tts -> publish), skipping
# ingest + write. Secrets come from the 0600 .env file, never from chat.
set -euo pipefail
cd "$(dirname "$0")"
set -a
source ./.env
set +a
# The runtime injects no_proxy/NO_PROXY with bracketed IPv6 literals
# ([::1], [fd8b:...]) which crashes httpx's proxy-bypass parsing
# (huggingface_hub -> httpx.InvalidURL). Unbracket them; matching still works.
for v in no_proxy NO_PROXY; do
  eval "val=\$$v"
  if [ -n "$val" ]; then
    val=$(echo "$val" | sed 's/\[//g; s/\]//g')
    export "$v=$val"
  fi
done
unset v val
export KOKORO_CACHE_DIR="${KOKORO_CACHE_DIR:-$PWD/.kokoro_cache}"
mkdir -p "$KOKORO_CACHE_DIR"
exec ./.venv/bin/python pipeline/run.py --mode "${1:-daily}" --skip ingest,write
