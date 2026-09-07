# ─────────────────────────────────────────────
# Stage 1 — install dependencies
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System libs needed by psycopg2, pdfplumber, python-docx, reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libffi-dev libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────
# Stage 2 — runtime image (smaller)
# ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libffi8 libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Create writable dirs for uploaded files at runtime
# (in production these map to Cloud Storage via FUSE or pre-signed URLs)
RUN mkdir -p static/letterheads static/report_images static/session_data \
             backend/data backend/data/registration backend/data/templates \
             backend/data/examples

# Index KPM documents into SQLite for RAG (runs at build time so DB is baked into image)
RUN python scripts/ingest_kpm_docs.py

# Cloud Run injects PORT env var — default 8080
ENV PORT=8080
EXPOSE 8080

# Use gunicorn for production (more stable than uvicorn --reload)
# Falls back to uvicorn if gunicorn not available
CMD ["sh", "-c", "python -m uvicorn app:app --host 0.0.0.0 --port $PORT --workers 2"]
