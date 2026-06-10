#!/usr/bin/env bash
# FAIRLADY — launch the game server.
#
#   ./run.sh                      # offline-safe defaults (stub narrator), real OSM routing
#   FAIRLADY_ADAPTER=ace ./run.sh # FAIRLADY's real voice via rop1's Ace stack (Nemotron + Kokoro)
#
# Env knobs (all optional):
#   FAIRLADY_ADAPTER   stub | ace                 (default: stub)
#   FAIRLADY_ROUTING   osm  | offline             (default: osm)
#   FAIRLADY_ACE_URL   Ace base url               (default: https://ace-api.badler.ai)
#   FAIRLADY_KOKORO_URL  OpenAI-compatible TTS for non-Japanese NPC voices (optional)
#   HOST / PORT        bind address / port        (default: 127.0.0.1 / 8739)
#
# NOTE: live OSM routing needs a Python built against a modern OpenSSL (3.x).
# macOS system/Xcode Python ships LibreSSL 2.8 and will fail the TLS handshake
# to the OSRM/Nominatim demo servers — use Homebrew python@3.12+ (this script's venv).
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if [ ! -d .venv ]; then
  echo "› creating venv with $PYTHON"
  "$PYTHON" -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
fi

export FAIRLADY_ADAPTER="${FAIRLADY_ADAPTER:-stub}"
export FAIRLADY_ROUTING="${FAIRLADY_ROUTING:-osm}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8739}"

echo "› FAIRLADY on http://$HOST:$PORT/  (adapter=$FAIRLADY_ADAPTER routing=$FAIRLADY_ROUTING)"
exec ./.venv/bin/python -m uvicorn app:app --app-dir backend --host "$HOST" --port "$PORT"
