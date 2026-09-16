#!/usr/bin/env bash
set -euo pipefail

echo "==> [greenbean] Running database migrations..."
python manage.py migrate --noinput

exec "$@"
