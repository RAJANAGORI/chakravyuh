#!/bin/bash

# Development startup: backend (FastAPI) + frontend (Next.js).
# Run ./setup-local.sh once first to install dependencies and optional Docker Postgres.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "🚀 Starting Chakravyuh in development mode..."
echo ""

cleanup() {
    echo ""
    echo "🛑 Stopping all services..."
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

echo "📦 Starting Backend (FastAPI on port 8000)..."
(cd "$ROOT/backend" && make api) &
BACKEND_PID=$!

sleep 3

# Use workspace dev from repo root so Next resolves from hoisted node_modules
echo "🎨 Starting Frontend (Next.js on port 3000)..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Services started!"
echo "   - Backend: http://localhost:8000"
echo "   - Frontend: http://localhost:3000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

wait
