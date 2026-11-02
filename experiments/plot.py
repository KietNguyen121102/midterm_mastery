#!/usr/bin/env python3
"""Charts for the three midterm experiments.

    python3 experiments/plot.py \
        --size results/aws/size.json \
        --loss results/aws/loss0.json results/aws/loss10.json results/aws/loss20.json \
        --locust results/aws/ramp25 \
        --watch results/aws/ramp25.watch.tsv \
        --out results/aws/figures
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "figure.dpi": 140,
    "font.size": 9,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

BLUE, ORANGE, GREEN, RED = "#2a6fb0", "#e08a28", "#3f8f5c", "#c53030"


def human_bytes(n: float) -> str:
    for unit, scale in (("MiB", 1024**2), ("KiB", 1024)):
        if n >= scale:
            return f"{n / scale:.0f} {unit}"
    return f"{n:.0f} B"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def chart_size(path: Path, out: Path) -> None:
    payload = load_json(path)
    rows = list(payload["rows"])
    if not rows:
        return
    labels = [human_bytes(r["bytes"]) for r in rows]
    med = [(r["median_millis"] or 0) / 1000 for r in rows]
    p95 = [(r["p95_millis"] or 0) / 1000 for r in rows]
    rates = [r["success_rate"] * 100 for r in rows]
    chunks = [r["chunks"] for r in rows]
    ok = [r["median_millis"] is not None for r in rows]

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    fig.suptitle("Experiment 1 — file size (loss=0, default retries)", fontsize=11)

    axes[0].plot([l for l, k in zip(labels, ok) if k],
                 [m for m, k in zip(med, ok) if k],
                 marker="o", color=BLUE, label="median")
    axes[0].plot([l for l, k in zip(labels, ok) if k],
                 [p for p, k in zip(p95, ok) if k],
                 marker="s", color=ORANGE, label="p95")
    axes[0].set_ylabel("seconds")
    ymax = max([p for p, k in zip(p95, ok) if k] + [3])
    axes[0].set_ylim(0, ymax * 1.15)
    axes[0].axhline(2.0, color="#a0aec0", ls="--", lw=0.8, label="2s quiet timeout")
    axes[0].set_title("Gateway latency (successes)")
    axes[0].legend(fontsize=8)

    axes[1].bar(labels, rates, color=GREEN, width=0.6)
    axes[1].set_ylim(0, 110)
    axes[1].set_ylabel("success %")
    axes[1].set_title("Completed transfers")
    for i, v in enumerate(rates):
        axes[1].text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=8)

    axes[2].bar(labels, chunks, color=BLUE, width=0.6)
    axes[2].set_ylabel("UDP chunks")
    axes[2].set_title("64-byte chunks in the file")

    fig.tight_layout()
    fig.savefig(out / "size.png")
    print(f"wrote {out / 'size.png'}")


def chart_loss(paths: list[Path], out: Path) -> None:
    series = []
    for path in paths:
        payload = load_json(path)
        for row in payload["rows"]:
            series.append(row)
    if not series:
        return
    # One file expected; group by send_loss.
    series.sort(key=lambda r: r["send_loss"])
    losses = [r["send_loss"] for r in series]
    rates = [r["success_rate"] * 100 for r in series]
    med = [(r["median_millis"] or 0) / 1000 for r in series]
    labels = [f"{loss}%" for loss in losses]

    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.4))
    fig.suptitle("Experiment 2 — send loss on a 64 KiB file (1024 chunks)", fontsize=11)

    axes[0].bar(labels, rates, color=GREEN, width=0.55)
    axes[0].set_ylim(0, 110)
    axes[0].set_ylabel("success %")
    axes[0].set_title("Completed transfers")
    for i, v in enumerate(rates):
        axes[0].text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=8)

    axes[1].bar(labels, med, color=ORANGE, width=0.55)
    axes[1].set_ylabel("seconds")
    axes[1].set_title("Median latency (successes)")

    fig.tight_layout()
    fig.savefig(out / "loss.png")
    print(f"wrote {out / 'loss.png'}")


def chart_load(locust_prefix: Path, watch: Path | None, out: Path) -> None:
    history = locust_prefix.with_name(locust_prefix.name + "_stats_history.csv")
    rows = []
    if history.exists():
        with history.open() as fh:
            for row in csv.DictReader(fh):
                if row.get("Name") != "Aggregated":
                    continue

                def num(key: str) -> float | None:
                    value = row.get(key, "")
                    return float(value) if value not in ("", "N/A") else None

                rows.append(
                    {
                        "users": num("User Count"),
                        "rps": num("Requests/s"),
                        "fps": num("Failures/s"),
                        "p50": num("50%"),
                        "p95": num("95%"),
                    }
                )

    watch_rows = []
    if watch and watch.exists():
        with watch.open() as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                watch_rows.append(row)

    fig, axes = plt.subplots(2, 2, figsize=(11, 6.2))
    fig.suptitle("Experiment 3 — Locust load vs gateway/backend scale", fontsize=11)
    x = list(range(len(rows)))
    if rows:
        axes[0][0].plot(x, [r["rps"] for r in rows], color=BLUE, label="req/s")
        axes[0][0].plot(x, [r["fps"] for r in rows], color=RED, label="fail/s")
        axu = axes[0][0].twinx()
        axu.step(x, [r["users"] for r in rows], color="#718096", where="post", label="users")
        axu.set_ylabel("users")
        axes[0][0].set_title("Locust rate")
        axes[0][0].set_ylabel("requests/s")
        axes[0][0].legend(loc="upper left", fontsize=8)

        axes[1][0].plot(x, [r["p50"] for r in rows], color=GREEN, label="p50")
        axes[1][0].plot(x, [r["p95"] for r in rows], color=ORANGE, label="p95")
        axes[1][0].set_title("Locust latency")
        axes[1][0].set_ylabel("ms")
        axes[1][0].legend(fontsize=8)

    if watch_rows:
        wx = list(range(len(watch_rows)))

        def col(name: str) -> list[float]:
            return [float(r[name]) for r in watch_rows]

        axes[0][1].step(wx, col("gw_desired"), where="post", color="#718096", label="desired")
        axes[0][1].step(wx, col("gw_running"), where="post", color=BLUE, label="running")
        axes[0][1].step(wx, col("gw_healthy"), where="post", color=GREEN, label="healthy")
        axes[0][1].set_title("Gateway tasks (ALB request-count scaler)")
        axes[0][1].set_ylabel("tasks")
        axes[0][1].set_ylim(0, 5)
        axes[0][1].legend(fontsize=8)

        axes[1][1].step(wx, col("be_desired"), where="post", color="#718096", label="desired")
        axes[1][1].step(wx, col("be_running"), where="post", color=ORANGE, label="running")
        axes[1][1].step(wx, col("be_healthy"), where="post", color=GREEN, label="healthy")
        axes[1][1].set_title("Backend tasks (CPU scaler)")
        axes[1][1].set_ylabel("tasks")
        axes[1][1].set_ylim(0, 5)
        axes[1][1].legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(out / "load.png")
    print(f"wrote {out / 'load.png'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size")
    parser.add_argument("--loss", nargs="*")
    parser.add_argument("--locust")
    parser.add_argument("--watch")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.size:
        chart_size(Path(args.size), out)
    if args.loss:
        chart_loss([Path(p) for p in args.loss], out)
    if args.locust:
        chart_load(Path(args.locust), Path(args.watch) if args.watch else None, out)


if __name__ == "__main__":
    main()
