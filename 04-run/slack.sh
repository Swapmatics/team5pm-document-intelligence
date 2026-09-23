#!/bin/sh
set -e
cd "$(dirname "$0")/.."
set -a
[ -f 04-run/.env ] && . ./04-run/.env
[ -f .env ] && . ./.env
set +a
export PYTHONPATH=02-src/desk:02-src/doors
exec /usr/bin/python3 02-src/doors/slack_door.py
