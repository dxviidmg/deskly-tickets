# syntax=docker/dockerfile:1

# --- Stage 1: build wheels for dependencies -------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
# Pre-build wheels so the final image doesn't need a compiler.
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# --- Stage 2: runtime image -----------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies from the prebuilt wheels.
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Application code.
COPY . .

# Ensure the entrypoint is executable regardless of the host's file mode.
RUN chmod +x entrypoint.sh

# Run as a non-root user.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Apply migrations, then start the server.
ENTRYPOINT ["bash", "./entrypoint.sh"]
