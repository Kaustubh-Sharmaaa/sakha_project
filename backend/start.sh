#!/usr/bin/env bash
# start.sh — Start the Sakha backend (SurrealDB + FastAPI)
# Usage:  ./start.sh           normal start
#         ./start.sh --reset   wipe DB and start fresh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SURREAL="$(command -v surreal 2>/dev/null || echo /opt/homebrew/bin/surreal)"
DB_PATH="$DIR/surreal_data"
LOG_DIR="$DIR/logs"
VENV="$DIR/.venv"
PORT=8080

mkdir -p "$LOG_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}ok${NC}  $*"; }
warn() { echo -e "${YELLOW}!!${NC}  $*"; }
fail() { echo -e "${RED}!!${NC}  $*"; exit 1; }

# --reset: wipe the database
if [[ "${1:-}" == "--reset" ]]; then
    warn "Resetting database..."
    pkill -f "surreal start" 2>/dev/null || true
    rm -rf "$DB_PATH"
    ok "Database wiped"
fi

# ── 1. SurrealDB ──────────────────────────────────────────────────────────────
test -x "$SURREAL" || fail "SurrealDB not found. Install: brew install surrealdb/tap/surreal"

if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    ok "SurrealDB already running"
else
    echo "   Starting SurrealDB..."
    mkdir -p "$DB_PATH"
    "$SURREAL" start --log warn --username root --password root "surrealkv://$DB_PATH" \
        >> "$LOG_DIR/surreal.log" 2>&1 &
    SURREAL_PID=$!
    for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
        sleep 0.5
        curl -sf http://localhost:8000/health >/dev/null 2>&1 && break || true
        test "$i" -eq 16 && fail "SurrealDB failed — check logs/surreal.log"
    done
    ok "SurrealDB started (pid $SURREAL_PID)"
fi

# ── 2. Apply indexes (safe to run every start — idempotent) ───────────────────
echo "   Applying indexes..."
"$SURREAL" sql -e http://localhost:8000 -u root -p root \
    --namespace sakha --database products < "$DIR/db_setup.surql" >/dev/null 2>&1
ok "Indexes applied"

# ── 3. Python venv ────────────────────────────────────────────────────────────
if test ! -d "$VENV"; then
    echo "   Creating virtual environment..."
    python3 -m venv "$VENV"
    ok "Venv created"
fi

# ── 4. Dependencies (only reinstall when requirements.txt changes) ─────────────
STAMP="$VENV/.install_stamp"
if test ! -f "$STAMP" || test "$DIR/requirements.txt" -nt "$STAMP"; then
    echo "   Installing dependencies..."
    "$VENV/bin/pip" install -q --upgrade pip
    "$VENV/bin/pip" install -q -r "$DIR/requirements.txt"
    touch "$STAMP"
    ok "Dependencies installed"
else
    ok "Dependencies up to date"
fi

# ── 5. FastAPI ────────────────────────────────────────────────────────────────
pkill -f "uvicorn main:app" 2>/dev/null || true
sleep 0.5

echo "   Starting FastAPI on port $PORT..."
cd "$DIR"
"$VENV/bin/uvicorn" main:app --reload --port "$PORT" \
    >> "$LOG_DIR/api.log" 2>&1 &
API_PID=$!

for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
    sleep 0.5
    curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1 && break || true
    test "$i" -eq 16 && fail "FastAPI failed — check logs/api.log"
done
ok "FastAPI started (pid $API_PID)"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}All systems go.${NC}"
echo ""
echo "   API  ->  http://localhost:$PORT"
echo "   Docs ->  http://localhost:$PORT/docs"
echo "   DB   ->  http://localhost:8000"
echo ""
echo "   Logs ->  $LOG_DIR/"
echo ""
echo "   Stop:  pkill -f 'surreal start'; pkill -f 'uvicorn main:app'"
