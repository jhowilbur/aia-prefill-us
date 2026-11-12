#!/usr/bin/env python3
"""Offline checks of this release.

1. form/ files match aia_us/form.py (build_form.py --check).
2. The checker gives the expected result on the three fictional fixtures.
3. If the pinned inventories are in data/raw/ (`make data`): SHA-256 match data/SOURCES.csv, and re-running
   the profile and the 2024->2025 diff reproduces reports/ byte for byte.

    python3 -I scripts/verify.py
"""
import csv
import filecmp
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = [sys.executable, "-I"]
RAW = ROOT / "data" / "raw"


def run(args):
    return subprocess.run(PY + [str(a) for a in args], capture_output=True, text=True, cwd=ROOT)


def main() -> int:
    fails = []
    r = run([ROOT / "scripts" / "build_form.py", "--check"])
    print("form files:", r.stdout.strip()); fails += [] if r.returncode == 0 else ["form"]
    expect = {"assessment_good.json": 0, "assessment_incomplete.md": 1, "assessment_boilerplate.json": 1}
    for f, code in expect.items():
        r = run([ROOT / "scripts" / "check_assessment.py", ROOT / "tests" / "fixtures" / f])
        n = sum(1 for line in r.stdout.splitlines() if line.startswith("  - "))
        ok = r.returncode == code
        print(f"checker {f}: exit {r.returncode}, {n} items listed", "OK" if ok else "UNEXPECTED")
        fails += [] if ok else [f]
    srcs = list(csv.DictReader(open(ROOT / "data" / "SOURCES.csv", encoding="utf-8")))
    have = [s for s in srcs if (RAW / s["local_file"]).exists()]
    if len(have) < len(srcs):
        print(f"pinned sources present: {len(have)}/{len(srcs)}; run `make data` for the data checks (skipped)")
    else:
        bad = [s["local_file"] for s in srcs if hashlib.sha256((RAW / s["local_file"]).read_bytes()).hexdigest() != s["sha256"]]
        print("SHA-256 of pinned sources:", "all match" if not bad else f"MISMATCH {bad}")
        fails += bad
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            run([ROOT / "scripts" / "profile_inventory.py", "--out", d / "profile_2025"])
            run([ROOT / "scripts" / "diff_inventories.py", RAW / "2024_consolidated_ai_inventory_raw_v2.csv",
                 RAW / "2025_individually_reported_AI_use_cases.csv", "--out", d / "diff_2024_2025"])
            for sub in ("profile_2025", "diff_2024_2025"):
                ref = ROOT / "reports" / sub
                files = sorted(p.name for p in ref.iterdir())
                _, mism, err = filecmp.cmpfiles(ref, d / sub, files, shallow=False)
                print(f"reports/{sub}: {len(files) - len(mism) - len(err)}/{len(files)} files reproduced byte for byte")
                fails += mism + err
    print("VERIFY", "OK" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
