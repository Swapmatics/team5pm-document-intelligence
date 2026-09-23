#!/bin/sh
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=02-src/desk:02-src/doors
export PYTHONUNBUFFERED=1
export PATH="/opt/homebrew/bin:/usr/bin:/bin:${PATH:-}"
export DOCKER_HOST="${DOCKER_HOST:-unix:///Users/dreserver/.colima/default/docker.sock}"
set -a
[ -f 04-run/.env ] && . ./04-run/.env
set +a
exec /usr/bin/python3 02-src/desk/server.py
