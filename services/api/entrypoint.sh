#!/bin/sh
set -e
if [ -n "$SYNC_DATABASE_URL" ]; then
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete."
fi
exec "$@"
