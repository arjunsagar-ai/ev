#!/usr/bin/env bash
set -e

# Root directory of the repository
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=========================================================="
echo " Starting Graph-Based EV Charging Station Optimization"
echo "=========================================================="

# Check system prerequisites
command -v python3 >/dev/null 2>&1 || { echo >&2 "[ERROR] Python 3 is required but not installed. Aborting."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo >&2 "[ERROR] npm is required but not installed. Aborting."; exit 1; }

# Setup backend virtual environment if not present
cd "$BACKEND_DIR"
if [ ! -d ".venv" ]; then
    echo "-> Creating Python virtual environment in backend/.venv..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "-> Installing backend Python dependencies..."
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Setup frontend environment and dependencies if not present
cd "$FRONTEND_DIR"
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "-> Creating frontend/.env from .env.example..."
    cp .env.example .env
fi

if [ ! -d "node_modules" ]; then
    echo "-> Installing frontend npm dependencies..."
    npm install
fi

# Clean up child processes on exit
CLEANED=0
cleanup() {
    if [ "$CLEANED" -eq 1 ]; then
        return
    fi
    CLEANED=1
    echo ""
    echo "Shutting down EV optimization services..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM EXIT

# Start backend
cd "$BACKEND_DIR"
echo "-> Starting Backend API server at http://127.0.0.1:8000 (Swagger docs: http://127.0.0.1:8000/docs)"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
cd "$FRONTEND_DIR"
echo "-> Starting Frontend UI at http://localhost:5173"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo " All services running!"
echo " - Web Application:   http://localhost:5173"
echo " - API Documentation: http://127.0.0.1:8000/docs"
echo " - API Base:          http://127.0.0.1:8000"
echo " Press Ctrl+C to stop all services."
echo "=========================================================="
echo ""

# Wait for background processes
wait
