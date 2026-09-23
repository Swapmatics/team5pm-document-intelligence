#!/bin/sh
# Call this after the desk is answering again. Parked files are read on the next pass.
set -eu
cd "$(dirname "$0")/.."
rm -f 04-run/updating 04-run/update-told.json
