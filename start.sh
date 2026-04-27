#!/usr/bin/env bash
# start.sh — Start the Sakha app (backend + frontend)
# Usage:
#   ./start.sh           normal start
#   ./start.sh --reset   wipe database and start fresh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_PORT=3000
LOG_DIR="$DIR/backend/logs"

GREEN='\033[0;32m'; NC='\033[0m'
ok() { echo -e "${GREEN}ok${NC}  $*"; }

mkdir -p "$LOG_DIR"

# ── 1. Backend (SurrealDB + FastAPI) ──────────────────────────────────────────
"$DIR/backend/start.sh" "$@"

# ── 2. Frontend static server on port 3000 ────────────────────────────────────
pkill -f "http.server $FRONTEND_PORT" 2>/dev/null || true
sleep 0.3

echo "   Starting frontend on port $FRONTEND_PORT..."
python3 -m http.server "$FRONTEND_PORT" --directory "$DIR" \
    >> "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

for i in 1 2 3 4 5 6; do
    sleep 0.5
    curl -sf "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 && break || true
    test "$i" -eq 6 && { echo "!! Frontend failed — check backend/logs/frontend.log"; exit 1; }
done
ok "Frontend started (pid $FRONTEND_PID)"

echo ""
echo -e "${GREEN}Ready.${NC}"
echo ""
echo "   App  ->  http://localhost:$FRONTEND_PORT"
echo ""
echo "   Stop frontend:  pkill -f 'http.server $FRONTEND_PORT'"
