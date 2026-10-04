# FinSight — executive cockpit container
# Build:  docker build -t finsight .
# Run:    docker run -p 8000:8000 [-e ANTHROPIC_API_KEY=sk-...] finsight
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=8000

WORKDIR /app

# Runtime deps only (no jupyter/matplotlib) — keeps the image small.
RUN pip install --no-cache-dir \
      "numpy>=1.24" "pandas>=2.0" "scikit-learn>=1.3" \
      "fastapi>=0.110" "uvicorn[standard]>=0.27" "pydantic>=2.0" \
      "anthropic>=0.39"

COPY src ./src
COPY api ./api

RUN useradd --create-home finsight
USER finsight

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=4)" || exit 1

# $PORT lets the same image run on Render / Fly / Cloud Run unchanged.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
