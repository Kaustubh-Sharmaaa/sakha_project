#!/usr/bin/env bash
# start_all.sh — Start both the Main Backend and Auth Microservice

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting Main Backend and Database...${NC}"
"$DIR/backend/start.sh"

echo -e "${GREEN}Starting Auth Microservice...${NC}"
cd "$DIR/surreal-auth-api/backend"

# Ensure venv exists
if [ ! -d ".venv" ]; then
    echo "   Creating virtual environment for Auth Microservice..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt -q

export PYTHONPATH="$(pwd)"

# Kill any existing instance
pkill -f "uvicorn app.main:app --host 0.0.0.0 --port 8001" 2>/dev/null || true
sleep 0.5

# Start in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload > auth.log 2>&1 &
AUTH_PID=$!

echo -e "${GREEN}ok${NC}  Auth Microservice started (pid $AUTH_PID)"
echo ""

echo -e "${GREEN}Starting Custom Frontend...${NC}"
cd "$DIR"

# Kill any existing simple http server on port 3000
pkill -f "python3 -m http.server 3000" 2>/dev/null || true
sleep 0.5

# Start in background
nohup python3 -m http.server 3000 > frontend.log 2>&1 &
FRONTEND_PID=$!

echo -e "${GREEN}ok${NC}  Custom Frontend started (pid $FRONTEND_PID)"
echo ""

echo -e "${GREEN}All systems go.${NC}"
echo "   Main API     ->  http://localhost:8080"
echo "   Auth API     ->  http://localhost:8001"
echo "   Frontend     ->  http://localhost:3000"
echo ""
echo "   Stop everything: pkill -f 'surreal start'; pkill -f 'uvicorn'; pkill -f 'python3 -m http.server'"
