#!/usr/bin/env bash
# HW6 watch_service.sh, adapted for two services behind two load balancers.
# Logs desired/running tasks for gateway and backend, plus ALB/NLB target health.
#
#   GATEWAY_TG=... BACKEND_TG=... experiments/watch.sh > results/aws/load.watch.tsv
set -u
CLUSTER=${CLUSTER:-file-transfer}
INTERVAL=${INTERVAL:-20}
GATEWAY_TG=${GATEWAY_TG:?set GATEWAY_TG}
BACKEND_TG=${BACKEND_TG:?set BACKEND_TG}

printf 'utc\tgw_desired\tgw_running\tgw_pending\tgw_healthy\tbe_desired\tbe_running\tbe_pending\tbe_healthy\n'
while true; do
  gw=$(aws ecs describe-services --cluster "$CLUSTER" --services gateway \
    --query 'services[0].[desiredCount,runningCount,pendingCount]' --output text)
  be=$(aws ecs describe-services --cluster "$CLUSTER" --services backend \
    --query 'services[0].[desiredCount,runningCount,pendingCount]' --output text)
  gw_states=$(aws elbv2 describe-target-health --target-group-arn "$GATEWAY_TG" \
    --query 'TargetHealthDescriptions[].TargetHealth.State' --output text | tr '\t' '\n')
  be_states=$(aws elbv2 describe-target-health --target-group-arn "$BACKEND_TG" \
    --query 'TargetHealthDescriptions[].TargetHealth.State' --output text | tr '\t' '\n')
  gw_healthy=$(printf '%s\n' "$gw_states" | grep -cx healthy)
  be_healthy=$(printf '%s\n' "$be_states" | grep -cx healthy)
  printf '%s\t%s\t%s\t%s\t%s\n' "$(date -u +%H:%M:%S)" "$(echo "$gw" | tr '\t' '\t')" "$gw_healthy" "$(echo "$be" | tr '\t' '\t')" "$be_healthy"
  sleep "$INTERVAL"
done
