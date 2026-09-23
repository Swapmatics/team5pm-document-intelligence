#!/bin/sh
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH=web
export PYTHONUNBUFFERED=1
exec /usr/bin/python3 web/mail_door.py
