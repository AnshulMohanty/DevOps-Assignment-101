#!/usr/bin/env bash
# Generate enough traffic on the backend to push CPU past the HPA target.
#   URL=http://taskboard.local/api/tasks ./scripts/load-test.sh            (through the Ingress)
#   kubectl run load -n taskboard --rm -i --image=curlimages/curl --command -- sh -c "$(cat scripts/load-test.sh)"
# /api/tasks queries PostgreSQL and serialises every task, so it costs real CPU;
# /health would barely register.
set -eu
URL="${URL:-http://taskboard-backend:8000/api/tasks}"
REQUESTS="${REQUESTS:-20000}"
CONCURRENCY="${CONCURRENCY:-20}"
seq 1 "$REQUESTS" | xargs -P "$CONCURRENCY" -I{} curl -s -o /dev/null "$URL"
echo "Load test completed: $REQUESTS requests to $URL"
