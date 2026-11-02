#!/usr/bin/env python3
"""HW4-style sweep of GET /files.

Two questions, two sweeps (run them separately so a loss redeploy is not
mixed into the size numbers):

  size   How does latency and throughput change as the file grows?
         Fixed: loss=0, default retries (5 OPEN / 5 RETY), default inflight.
         Vary:  file size.

  loss   What does simulated datagram loss do to success and latency?
         Fixed: one file (64 KiB = 1024 chunks).
         Vary:  backend SEND_LOSS (set at deploy time).

    python3 experiments/sweep.py --host http://127.0.0.1:8082 \
        --files f4kib.bin,f64kib.bin --reps 5 \
        --label size-local --loss 0 \
        --out results/local/size.json

Stdlib only. Each request is timed from the HTTP client's point of view, which
is what a real caller of the gateway sees.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

SIZES = {
    "f4kib.bin": 4 * 1024,
    "f64kib.bin": 64 * 1024,
    "f256kib.bin": 256 * 1024,
    "f1mib.bin": 1024 * 1024,
    "f4mib.bin": 4 * 1024 * 1024,
}


def fetch(host: str, name: str, timeout: float) -> dict:
    url = f"{host.rstrip('/')}/files?name={name}"
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
            elapsed = (time.perf_counter() - started) * 1000
            return {
                "ok": True,
                "status": resp.status,
                "bytes": len(body),
                "millis": elapsed,
            }
    except urllib.error.HTTPError as err:
        elapsed = (time.perf_counter() - started) * 1000
        return {
            "ok": False,
            "status": err.code,
            "bytes": 0,
            "millis": elapsed,
            "error": err.read().decode("utf-8", "replace")[:200],
        }
    except Exception as err:
        elapsed = (time.perf_counter() - started) * 1000
        return {
            "ok": False,
            "status": 0,
            "bytes": 0,
            "millis": elapsed,
            "error": str(err),
        }


def summarize(name: str, expected: int, loss: int, records: list[dict]) -> dict:
    oks = [r for r in records if r["ok"] and r["bytes"] == expected]
    times = [r["millis"] for r in oks]
    statuses: dict[str, int] = {}
    for r in records:
        key = str(r["status"])
        statuses[key] = statuses.get(key, 0) + 1
    chunks = (expected + 63) // 64
    median_ms = statistics.median(times) if times else None
    p95_ms = None
    if times:
        ordered = sorted(times)
        p95_ms = ordered[min(len(ordered) - 1, max(0, round(0.95 * (len(ordered) - 1))))]
    mb_per_sec = None
    if median_ms and median_ms > 0:
        mb_per_sec = expected / 1024 / 1024 / (median_ms / 1000)
    return {
        "file": name,
        "bytes": expected,
        "chunks": chunks,
        "send_loss": loss,
        "reps": len(records),
        "successes": len(oks),
        "success_rate": len(oks) / len(records) if records else 0,
        "statuses": statuses,
        "median_millis": median_ms,
        "p95_millis": p95_ms,
        "min_millis": min(times) if times else None,
        "max_millis": max(times) if times else None,
        "mb_per_sec": mb_per_sec,
        "runs": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--files", default="f4kib.bin,f64kib.bin,f256kib.bin,f1mib.bin")
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--label", required=True)
    parser.add_argument("--loss", type=int, default=0, help="SEND_LOSS the server was deployed with")
    parser.add_argument("--sleep", type=float, default=0.2, help="pause between requests")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    names = [n.strip() for n in args.files.split(",") if n.strip()]
    rows = []
    for name in names:
        if name not in SIZES:
            raise SystemExit(f"unknown file {name!r}")
        expected = SIZES[name]
        print(f"==> {name}  {expected} bytes  {args.reps} reps  loss={args.loss}")
        records = []
        for i in range(args.reps):
            result = fetch(args.host, name, args.timeout)
            records.append(result)
            flag = "ok" if result["ok"] else f"FAIL {result['status']}"
            print(f"    [{i + 1}/{args.reps}] {flag}  {result['millis']:.0f} ms  {result['bytes']} B")
            time.sleep(args.sleep)
        rows.append(summarize(name, expected, args.loss, records))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": args.label,
        "host": args.host,
        "send_loss": args.loss,
        "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rows": rows,
    }
    out.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
