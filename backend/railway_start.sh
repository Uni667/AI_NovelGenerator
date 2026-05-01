#!/bin/bash
# Railway startup: write config from env var, then start server

echo "Writing config.json from RAILWAY_CONFIG_JSON..."
echo "$RAILWAY_CONFIG_JSON" > /app/config.json

# Set PYTHONPATH so backend can import desktop modules
export PYTHONPATH="/app:$PYTHONPATH"

# Ensure data directory exists
mkdir -p /app/data

echo "Starting FastAPI server..."
cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
