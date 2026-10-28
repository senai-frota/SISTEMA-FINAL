#!/bin/sh
set -e

MEDIA_ROOT="${MEDIA_ROOT:-/app/media}"
STATIC_ROOT="${STATIC_ROOT:-/app/staticfiles}"
mkdir -p "$MEDIA_ROOT" "$STATIC_ROOT"

echo "Aguardando PostgreSQL em ${DB_HOST:-db}:${DB_PORT:-5432}..."
python <<'PY'
import os
import sys
import time

import psycopg2

host = os.environ.get("DB_HOST", "db")
port = os.environ.get("DB_PORT", "5432")
name = os.environ.get("DB_NAME", "frota")
user = os.environ.get("DB_USER", "frota")
password = os.environ.get("DB_PASSWORD", "")
sslmode = os.environ.get("DB_SSLMODE", "disable")

# Tempo generoso para primeiro boot / disco lento; em falha o restart do Compose retenta.
deadline = time.time() + 120
last_error = None
while time.time() < deadline:
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=name,
            user=user,
            password=password,
            sslmode=sslmode,
            connect_timeout=3,
        )
        conn.close()
        print(f"PostgreSQL disponível em {host}:{port}.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 — aguarda disponibilidade
        last_error = exc
        time.sleep(2)

print(f"PostgreSQL indisponível após 120s: {last_error}", file=sys.stderr)
sys.exit(1)
PY

if [ "${SKIP_MIGRATE:-}" != "1" ]; then
    echo "Aplicando migrations..."
    python manage.py migrate --noinput
else
    echo "SKIP_MIGRATE=1: migrations não aplicadas neste processo."
fi

if [ "${SKIP_COLLECTSTATIC:-}" != "1" ]; then
    echo "Coletando arquivos estáticos..."
    python manage.py collectstatic --noinput
else
    echo "SKIP_COLLECTSTATIC=1: collectstatic ignorado."
fi

echo "Iniciando: $*"
exec "$@"
