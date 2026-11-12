#!/usr/bin/env python3
"""Download the pinned inventory files listed in data/SOURCES.csv into data/raw/ and check SHA-256.

    python3 -I scripts/fetch_inventory.py
"""
import csv
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    bad = 0
    for r in csv.DictReader(open(ROOT / "data" / "SOURCES.csv", encoding="utf-8")):
        dst = RAW / r["local_file"]
        if not dst.exists() or hashlib.sha256(dst.read_bytes()).hexdigest() != r["sha256"]:
            req = urllib.request.Request(r["url"], headers={"User-Agent": "aia-prefill-us-fetch"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                dst.write_bytes(resp.read())
        got = hashlib.sha256(dst.read_bytes()).hexdigest()
        ok = got == r["sha256"]
        bad += not ok
        print(("OK  " if ok else "BAD ") + r["local_file"])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
