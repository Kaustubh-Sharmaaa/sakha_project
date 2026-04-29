#!/usr/bin/env bash
# start_auth.sh
# Starts the Auth Microservice on port 8001

set -e
cd "$(dirname "$0")"

echo "==========================================="
echo " Starting Sakha Auth Microservice (Port 8001)"
echo "==========================================="

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt -q

# Set PYTHONPATH to the backend directory so 'app' can be found
export PYTHONPATH="$(pwd)"

uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
