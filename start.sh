#!/usr/bin/env bash

# Exit on error
set -e

# Ensure the local Node/NPM binary directory is in the PATH
export PATH="$PWD/.node-dist/bin:$PATH"

echo "=== Kapital Startup Script ==="

# Check dependencies
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' is not installed or not in PATH."
    echo "Please install it: https://github.com/astral-sh/uv"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Error: 'npm' is not installed or not in PATH."
    echo "Make sure '.node-dist' directory is present in the workspace root."
    exit 1
fi

# Track pids of backend and frontend
BACKEND_PID=""
FRONTEND_PID=""

# Graceful cleanup on exit/SIGINT/SIGTERM
cleanup() {
    echo ""
    echo "Shutting down servers..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "Servers stopped cleanly."
}

# Register traps
trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo "Starting FastAPI backend server..."
uv run --directory backend uvicorn src.main:app --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting Vue.js frontend server..."
npm run dev --prefix frontend &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
