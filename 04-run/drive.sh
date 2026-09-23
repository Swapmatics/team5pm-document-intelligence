#!/bin/sh
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=02-src/desk:02-src/doors
export PYTHONUNBUFFERED=1
exec /usr/bin/python3 02-src/doors/drive_door.py
