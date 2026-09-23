#!/bin/sh
# Queue-mode n8n on the Mac. Postgres, Redis, and MinIO come from docker compose.
set -eu
cd "$(dirname "$0")"
set -a
. ./.env
set +a

runtime="$(pwd)/n8n-runtime"
node_bin="${NODE_BIN:-/opt/homebrew/opt/node@22/bin/node}"
if [ ! -x "$runtime/bin/n8n" ]; then
  echo "n8n runtime is missing. Run the copy from the n8n image into 04-run/n8n-runtime." >&2
  exit 1
fi
mkdir -p n8n-data
export N8N_USER_FOLDER="$(pwd)/n8n-data"
export DB_TYPE=postgresdb
export DB_POSTGRESDB_HOST=127.0.0.1
export DB_POSTGRESDB_PORT=5436
export DB_POSTGRESDB_DATABASE=n8n
export DB_POSTGRESDB_USER=n8n
export DB_POSTGRESDB_PASSWORD="$N8N_DB_PASSWORD"
export EXECUTIONS_MODE=queue
export QUEUE_BULL_REDIS_HOST=127.0.0.1
export QUEUE_BULL_REDIS_PORT=6381
export OFFLOAD_MANUAL_EXECUTIONS_TO_WORKERS=true
export N8N_ENCRYPTION_KEY
export N8N_HOST=127.0.0.1
export N8N_PORT=5680
export N8N_PROTOCOL=http
export N8N_SECURE_COOKIE=false
export WEBHOOK_URL=http://127.0.0.1:5680/
export N8N_OWNER_EMAIL
export N8N_OWNER_PASSWORD
export N8N_OWNER_FIRST_NAME=Andre
export N8N_OWNER_LAST_NAME=Naidoo
export GENERIC_TIMEZONE=Africa/Johannesburg
export N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=false

if [ "${1:-}" = "worker" ]; then
  exec "$node_bin" "$runtime/bin/n8n" worker
fi
exec "$node_bin" "$runtime/bin/n8n"
