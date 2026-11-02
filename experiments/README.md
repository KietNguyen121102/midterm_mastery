# Midterm experiments

Three focused runs, using the same style of tools as HW4–HW6. Settings that
stay fixed, and the one knob each run changes, are listed below so the
combinatorial explosion the assignment warns about does not happen.

| | Experiment 1 | Experiment 2 | Experiment 3 |
|---|---|---|---|
| Question | How does size change latency? | How far do 5 RETY rounds cover loss? | Do the two scalers even fire? |
| HW tool | HW4 size sweep + charts | HW4 parameter sweep | HW5/6 Locust + service watch |
| Fixed | loss=0, retries=5/5, inflight=4, workers=8 | 64 KiB file, retries=5/5 | 64 KiB file, loss=0 |
| Vary | file size: 4 KiB … 4 MiB | `SEND_LOSS` 0 / 10 / 20 | concurrent Locust users |
| Metric | median / p95 latency, goodput | success rate, latency | RPS, 503s, gateway vs backend tasks |

Gateway scaler: `ALBRequestCountPerTarget` (40 req/min/task in tfvars).
Backend scaler: `ECSServiceAverageCPUUtilization` (40%). An NLB has no
per-target request metric, which is the point of experiment 3.

## Local dry run

```bash
python3 experiments/make_files.py --out experiments/corpus
go build -o bin/backend ./transfer-server
go build -o bin/gateway ./transfer-frontend
bin/backend udp -dir=experiments/corpus -port=8080 -health-port=8081 &
bin/gateway -transport=udp -upstream=localhost:8080 -listen=:8082 &
python3 experiments/sweep.py --host http://127.0.0.1:8082 \
  --files f4kib.bin,f64kib.bin --reps 3 --label size-local --loss 0 \
  --out results/local/size.json
```

## AWS

Learner Lab credentials must be valid (`aws sts get-caller-identity`).

```bash
experiments/bootstrap_aws.sh
scripts/deploy.sh --yes
export HOST=http://$(terraform -chdir=terraform output -raw alb_dns_name)

python3 experiments/sweep.py --host "$HOST" --label size-aws --loss 0 \
  --files f4kib.bin,f64kib.bin,f256kib.bin,f1mib.bin --reps 5 \
  --out results/aws/size.json

# 4 MiB is the protocol cap; two reps only (65536 datagrams each).
python3 experiments/sweep.py --host "$HOST" --label size-4mib --loss 0 \
  --files f4mib.bin --reps 2 --timeout 90 --out results/aws/size-4mib.json

NAME=ramp25 USERS=25 SPAWN=5 DURATION=8m HOST="$HOST" experiments/run_load.sh

# Loss points need a redeploy. Images stay the same.
scripts/deploy.sh --yes --skip-build --var backend_send_loss=10
python3 experiments/sweep.py --host "$HOST" --files f64kib.bin --reps 8 \
  --label loss10 --loss 10 --out results/aws/loss10.json
scripts/deploy.sh --yes --skip-build --var backend_send_loss=20
python3 experiments/sweep.py --host "$HOST" --files f64kib.bin --reps 8 \
  --label loss20 --loss 20 --out results/aws/loss20.json

python3 experiments/plot.py \
  --size results/aws/size.json \
  --loss results/aws/size.json results/aws/loss10.json results/aws/loss20.json \
  --locust results/aws/ramp25 \
  --watch results/aws/ramp25.watch.tsv \
  --out results/aws/figures
```

Tear down when the presentation numbers are in: `scripts/destroy.sh --yes`.
