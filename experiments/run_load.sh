#!/usr/bin/env bash
# HW6 part3_scale_run.sh, pointed at the file-transfer gateway.
#
#   HOST=http://<ALB> NAME=ramp25 USERS=25 DURATION=8m experiments/run_load.sh
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

NAME=${NAME:?}
USERS=${USERS:-25}
SPAWN=${SPAWN:-5}
DURATION=${DURATION:-8m}
HOST=${HOST:?set HOST to http://<alb-dns>}
FILE=${FILE:-f64kib.bin}
LOCUST=${LOCUST:-/Users/nguyen/Documents/CS6650/hw5/locust/.venv/bin/locust}
OUT=${OUT:-results/aws}
CLUSTER=${CLUSTER:-file-transfer}
export FILE
mkdir -p "$OUT"

if [[ -z "${GATEWAY_TG:-}" ]]; then
  GATEWAY_TG=$(aws elbv2 describe-target-groups --names file-transfer-gateway \
    --query 'TargetGroups[0].TargetGroupArn' --output text)
fi
if [[ -z "${BACKEND_TG:-}" ]]; then
  BACKEND_TG=$(aws elbv2 describe-target-groups --names file-transfer-backend \
    --query 'TargetGroups[0].TargetGroupArn' --output text)
fi
export GATEWAY_TG BACKEND_TG CLUSTER

experiments/watch.sh > "$OUT/$NAME.watch.tsv" 2>&1 &
WATCH=$!
trap 'kill $WATCH 2>/dev/null || true' EXIT

echo "$NAME start $(date -u +%Y-%m-%dT%H:%M:%SZ) users=$USERS spawn=$SPAWN duration=$DURATION file=$FILE host=$HOST" | tee -a "$OUT/timeline.txt"

"$LOCUST" -f experiments/locustfile.py --headless --host "$HOST" \
  -u "$USERS" -r "$SPAWN" -t "$DURATION" \
  --csv "$OUT/$NAME" --csv-full-history --html "$OUT/$NAME.html" --only-summary \
  > "$OUT/$NAME.log" 2>&1 || true

echo "$NAME end $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$OUT/timeline.txt"
grep -E 'Aggregated|Error' "$OUT/$NAME.log" | head -5 || true
