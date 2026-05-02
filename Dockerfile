FROM python:3.12-slim

WORKDIR /app

# Install only the cloud backend dependencies (no torch/transformers/chromadb)
COPY backend/requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

# Copy all Python source code (the backend imports from root-level modules)
COPY backend/ backend/
COPY llm_adapters.py .
COPY embedding_adapters.py .
COPY prompt_definitions.py .
COPY utils.py .
COPY chapter_directory_parser.py .
COPY consistency_checker.py .
COPY novel_generator/ novel_generator/

# Ensure data directory
RUN mkdir -p /app/data

# Railway provides PORT env var
EXPOSE 8001

# Startup: start uvicorn directly (no config_manager dependency)
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8001} --timeout-keep-alive 300' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
