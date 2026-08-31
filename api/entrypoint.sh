#!/usr/bin/env bash
# Entrypoint: wait for the database, apply migrations, then start the server.
set -euo pipefail

echo "Applying database migrations (alembic upgrade head)..."
# Retry a few times in case the database is not accepting connections yet.
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  if alembic upgrade head; then
    echo "Migrations applied."
    break
  fi
  echo "Database not ready yet (attempt ${attempt}); retrying in 2s..."
  sleep 2
done

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
