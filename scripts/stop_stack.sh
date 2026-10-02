#!/usr/bin/env bash
# Stops the local HAPI FHIR server. Pass -v to also wipe its data volume.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "-v" ]]; then
  docker compose down -v
  echo "Stack stopped and data volume removed."
else
  docker compose down
  echo "Stack stopped. Data volume preserved (use 'stop_stack.sh -v' to wipe it)."
fi
