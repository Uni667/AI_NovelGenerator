FROM python:3.12-slim

WORKDIR /app

# Install only the cloud backend dependencies (no torch/transformers/chromadb)
COPY backend/requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

# Copy all Python source code (the backend imports from root-level modules)
COPY backend/ backend/
COPY llm_adapters.py .
COPY embedding_adapters.py .
COPY utils.py .
COPY chapter_directory_parser.py .
COPY consistency_checker.py .
COPY llm_errors.py .
COPY novel_generator/ novel_generator/

# Copy seed data (local users, projects, chapters) — baked into the image
# but only used when the persistent disk is empty (first deploy)
COPY docker_seed/ /app/docker_seed/

# Ensure data directory
RUN mkdir -p /app/data

# Platform (Railway / Render) provides PORT env var
EXPOSE 8001

# Startup script: seed data on first deploy, then start uvicorn
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo '# On first deploy, seed the persistent disk with baked-in data' >> /app/start.sh && \
    echo 'if [ ! -f /app/data/projects.db ]; then' >> /app/start.sh && \
    echo '  echo "[entrypoint] First deploy detected — seeding initial data..."' >> /app/start.sh && \
    echo '  cp /app/docker_seed/projects.db /app/data/projects.db' >> /app/start.sh && \
    echo '  if [ -d /app/docker_seed/projects ]; then' >> /app/start.sh && \
    echo '    cp -r /app/docker_seed/projects /app/data/projects' >> /app/start.sh && \
    echo '  fi' >> /app/start.sh && \
    echo '  echo "[entrypoint] Seed complete. Data will persist across restarts."' >> /app/start.sh && \
    echo 'else' >> /app/start.sh && \
    echo '  echo "[entrypoint] Existing data found — using persistent disk."' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo 'exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8001} --timeout-keep-alive 300' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
