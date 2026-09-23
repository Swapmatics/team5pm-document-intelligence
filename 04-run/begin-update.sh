#!/bin/sh
# Call this before a restart. Doors keep new files and tell the person.
set -eu
cd "$(dirname "$0")/.."
mkdir -p 04-run
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > 04-run/updating
