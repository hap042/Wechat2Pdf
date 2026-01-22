#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    
    # Kill specific processes if they are running
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    # Wait for them to finish shutting down (prevents logs appearing after prompt)
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    
    echo "All services stopped."
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

echo "=================================================="
echo "      WeChat Article to PDF - Local Dev Start     "
echo "=================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm could not be found."
    exit 1
fi

# 1. Backend Setup
echo "[1/3] Checking Backend..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
else
    echo "Backend dependencies found."
fi

# 2. Frontend Setup
echo "[2/3] Checking Frontend..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
else
    echo "Frontend dependencies found."
fi

# 3. Start Services
echo "[3/3] Starting Services..."

# Start Backend in background
echo "Starting Backend (FastAPI) on port 8000..."
python3 -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Frontend in background
echo "Starting Frontend (Vite) on port 5173..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo "--------------------------------------------------"
echo "✅ System is running!"
echo "🌍 Frontend: http://localhost:5173"
echo "🔌 Backend:  http://localhost:8000"
echo "--------------------------------------------------"
echo "Press Ctrl+C to stop all services."

# Wait for both processes
wait
