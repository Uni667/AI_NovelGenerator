#!/bin/bash
# Railway startup script
set -e

export PYTHONPATH="/app:$PYTHONPATH"
mkdir -p /app/data

echo "Starting FastAPI server..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8001}
