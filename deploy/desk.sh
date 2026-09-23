#!/bin/sh
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=web
export PYTHONUNBUFFERED=1
export PATH="/opt/homebrew/bin:/usr/bin:/bin:${PATH:-}"
export DOCKER_HOST="${DOCKER_HOST:-unix:///Users/dreserver/.colima/default/docker.sock}"
set -a
[ -f deploy/.env ] && . ./deploy/.env
set +a
exec /usr/bin/python3 web/server.py
