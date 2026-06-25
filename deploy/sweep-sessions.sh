#!/usr/bin/env bash
# Prune abandoned web-session saves (and their rewind checkpoints) older than N days.
# Each visitor leaves a data/saves/web_<token>.json (+ cp_<token>_*.json); this reclaims the
# stale ones. Safe to run live — it only removes files untouched for the cutoff window.
#
#   ./sweep-sessions.sh [SAVES_DIR] [DAYS]
#   ./sweep-sessions.sh /opt/fairlady/data/saves 30
set -euo pipefail
SAVES="${1:-/opt/fairlady/data/saves}"
DAYS="${2:-30}"
[ -d "$SAVES" ] || { echo "sweep-sessions: no saves dir at $SAVES" >&2; exit 1; }

n=0
while IFS= read -r -d '' f; do
	base="$(basename "$f" .json)"        # web_<token>
	token="${base#web_}"
	rm -f -- "$f"
	rm -f -- "$SAVES"/cp_"$token"_*.json
	n=$((n + 1))
done < <(find "$SAVES" -maxdepth 1 -name 'web_*.json' -mtime +"$DAYS" -print0)

echo "sweep-sessions: removed $n abandoned session(s) older than ${DAYS}d from $SAVES"
