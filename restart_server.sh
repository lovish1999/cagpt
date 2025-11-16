#!/bin/bash
# restart_server.sh - Automatically restart the CA-GPT server

echo "🔍 Checking for existing server on port 8000..."
PID=$(lsof -ti:8000)

if [ ! -z "$PID" ]; then
    echo "⚠️  Found existing process (PID: $PID), killing it..."
    kill -9 $PID
    sleep 1
    echo "✅ Old server stopped"
else
    echo "✅ No existing server found"
fi

echo "🚀 Starting CA-GPT server..."
python3 ca_agent_tools.py
