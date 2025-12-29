#!/bin/bash

echo "🚀 Starting ESG Data Extraction System"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Start backend
echo "📡 Starting FastAPI backend on port 8000..."
source venv/bin/activate
uvicorn api:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "🎨 Starting React frontend on port 3000..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "📦 Installing React dependencies..."
    npm install
fi

npm start &
FRONTEND_PID=$!

echo ""
echo "✅ System is running!"
echo "========================================"
echo "📡 Backend API: http://localhost:8000"
echo "📡 API Docs: http://localhost:8000/docs"
echo "🎨 Frontend UI: http://localhost:3000"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
wait $BACKEND_PID $FRONTEND_PID
