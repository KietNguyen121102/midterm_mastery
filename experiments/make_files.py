#!/usr/bin/env python3
"""Write files of exact sizes for the transfer experiments.

Same idea as HW4's make_corpus.py: known sizes, seeded contents, no surprise
downloads. File names stay plain (no '/', no leading '.') so they are legal
FTP_6650 names.

    python3 experiments/make_files.py --out experiments/corpus
"""
from __future__ import annotations

import argparse
import pathlib

# Exact byte sizes. 4 MiB is the client's maxChunks cap (65536 * 64).
SIZES = {
    "f4kib.bin": 4 * 1024,
    "f64kib.bin": 64 * 1024,
    "f256kib.bin": 256 * 1024,
    "f1mib.bin": 1024 * 1024,
    "f4mib.bin": 4 * 1024 * 1024,
}


def write_file(path: pathlib.Path, n: int) -> None:
    """Deterministic filler so two runs compare byte-for-byte."""
    # A repeating 256-byte pattern is cheap to generate and not compressible
    # into fewer UDP chunks: the protocol always uses 64-byte payloads.
    block = bytes((i + (n % 251)) % 256 for i in range(256))
    path.write_bytes((block * (n // 256 + 1))[:n])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="experiments/corpus")
    parser.add_argument("--sizes", default=",".join(SIZES))
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = [name.strip() for name in args.sizes.split(",") if name.strip()]
    for name in wanted:
        if name not in SIZES:
            raise SystemExit(f"unknown size name {name!r}; choose from {list(SIZES)}")
        path = out / name
        write_file(path, SIZES[name])
        chunks = (SIZES[name] + 63) // 64
        print(f"{path}  {SIZES[name]} bytes  {chunks} chunks")


if __name__ == "__main__":
    main()
