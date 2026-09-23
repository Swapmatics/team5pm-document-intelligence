#!/bin/sh
set -e
cd "$(dirname "$0")/.."
set -a
[ -f deploy/.env ] && . ./deploy/.env
[ -f .env ] && . ./.env
set +a
export PYTHONPATH=web
exec /usr/bin/python3 web/slack_door.py
