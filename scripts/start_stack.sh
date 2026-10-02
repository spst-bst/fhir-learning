#!/usr/bin/env bash
# Starts the local HAPI FHIR server and waits until it's ready to accept requests.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up -d

echo "Waiting for HAPI FHIR to become ready on http://localhost:8080/fhir ..."
for i in $(seq 1 60); do
  if curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/fhir/metadata | grep -q '^200$'; then
    echo "HAPI FHIR is up: http://localhost:8080/fhir"
    exit 0
  fi
  sleep 3
done

echo "Timed out waiting for HAPI FHIR to start. Check logs with: docker compose logs hapi-fhir" >&2
exit 1
