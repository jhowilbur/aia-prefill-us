#!/usr/bin/env python3
"""Profile the pinned 2025 U.S. federal AI use-case inventory (offline, stdlib only).

Reads data/raw/2025_individually_reported_AI_use_cases.csv (git-ignored; fetched by
scripts/fetch_inventory.py), checks its SHA-256 against data/SOURCES.csv, and writes
reports/inventory_profile.json and reports/hi_field_completeness.csv. Free text and the
contact_email column are never written out: only counts.

    python3 -I scripts/profile_inventory.py [path/to/csv] [--out DIR]
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "2025_individually_reported_AI_use_cases.csv"
EMPTY = {"", "nan", "none", "n/a", "na", "null", "-", "[]"}

# Inventory columns that the 2025 data call ties to an M-25-21 Section 4(b) practice
# (per the data dictionary's own "Practice:" labels and "consistent with Section 4(b)(x)").
HI_FIELDS = {
    "hi_testing_conducted": "4(b)(i) pre-deployment testing",
    "hi_assessment_completed": "4(b)(ii) AI impact assessment (completed?)",
    "hi_potential_impacts": "4(b)(ii) impact assessment: potential impacts (free text)",
    "hi_independent_review": "4(b)(ii) impact assessment: independent review",
    "hi_ongoing_monitoring": "4(b)(iii) ongoing monitoring",
    "hi_training_established": "4(b)(iv) human training and assessment",
    "hi_failsafe_presence": "4(b)(v) human oversight / fail-safe",
    "hi_appeal_process": "4(b)(vi) remedies or appeals",
    "hi_public_consultation": "4(b)(vii) end-user and public feedback",
}
# General columns that may carry evidence for 4(b)(ii) sub-items (A)-(C).
CONTEXT_FIELDS = ["problem_solved", "benefits", "system_outputs", "data_description",
                  "link_to_data", "has_pii", "pia_url", "demographic_features", "have_ato"]


def present(v: str | None) -> bool:
    return v is not None and v.strip().lower() not in EMPTY


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bucket(v: str) -> str:
    """Multiple-choice value as reported; values over 80 characters (free text typed into a choice column) are
    counted under one label so that no free text is copied out."""
    v = v.strip()
    return v if len(v) <= 80 else "(value over 80 characters, not shown)"


def is_hi(r: dict) -> bool:
    return r.get("is_high_impact", "").strip().lower() == "high-impact"


def stage(r: dict) -> str:
    return r.get("development_stage", "").strip()


def profile(rows: list[dict], columns: list[str]) -> dict:
    hi = [r for r in rows if is_hi(r)]
    hi_dep = [r for r in hi if stage(r) == "Deployed"]
    dep_pilot = [r for r in rows if stage(r) in ("Deployed", "Pilot")]
    def comp(subset, fields):
        n = len(subset)
        return {f: {"present": sum(present(r.get(f)) for r in subset), "n": n} for f in fields}
    return {
        "n_rows": len(rows),
        "n_columns": len(columns),
        "columns": columns,
        "n_agencies": len({r.get("agency", "") for r in rows}),
        "rows_with_id": sum(bool(r.get("id", "").strip()) for r in rows),
        "distinct_nonblank_ids": len({r["id"].strip() for r in rows if r.get("id", "").strip()}),
        "development_stage": dict(Counter(stage(r) for r in rows).most_common()),
        "deployed_plus_pilot": len(dep_pilot),
        "is_high_impact": dict(Counter(r.get("is_high_impact", "").strip() for r in rows).most_common()),
        "high_impact": len(hi),
        "high_impact_by_stage": dict(Counter(stage(r) for r in hi).most_common()),
        "high_impact_by_agency": dict(Counter(r.get("agency", "") for r in hi).most_common()),
        "high_impact_deployed": len(hi_dep),
        "hi_value_counts_deployed": {f: dict(Counter(bucket(r.get(f, "")) for r in hi_dep).most_common())
                                     for f in HI_FIELDS if f != "hi_potential_impacts"},
        "completeness_hi_all": comp(hi, list(HI_FIELDS) + CONTEXT_FIELDS),
        "completeness_hi_deployed": comp(hi_dep, list(HI_FIELDS) + CONTEXT_FIELDS),
        "hi_potential_impacts_chars_deployed": sorted(len(r.get("hi_potential_impacts", "").strip())
                                                      for r in hi_dep if present(r.get("hi_potential_impacts"))),
    }


def main() -> int:
    argv = sys.argv[1:]
    out = ROOT / "reports"
    if "--out" in argv:
        i = argv.index("--out")
        out = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    path = Path(argv[0]) if argv else RAW
    if not path.exists():
        print(f"missing {path.name}: run `make data` first", file=sys.stderr)
        return 2
    pinned = {r["local_file"]: r["sha256"] for r in csv.DictReader(open(ROOT / "data" / "SOURCES.csv", encoding="utf-8"))}
    got = sha256(path)
    if path == RAW and pinned.get(path.name) != got:
        print(f"SHA-256 mismatch for {path.name}: {got}", file=sys.stderr)
        return 1
    with open(path, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        rows, columns = list(rd), list(rd.fieldnames or [])
    p = profile(rows, columns)
    p["source_sha256"] = got
    p["hi_potential_impacts_chars_deployed"] = {
        "n": len(p["hi_potential_impacts_chars_deployed"]),
        "median": (p["hi_potential_impacts_chars_deployed"][len(p["hi_potential_impacts_chars_deployed"]) // 2]
                   if p["hi_potential_impacts_chars_deployed"] else None),
        "under_100_chars": sum(c < 100 for c in p["hi_potential_impacts_chars_deployed"]),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory_profile.json").write_text(json.dumps(p, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(out / "hi_field_completeness.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["field", "m25_21_practice", "present_hi_all", "n_hi_all", "present_hi_deployed", "n_hi_deployed"])
        for fld in list(HI_FIELDS) + CONTEXT_FIELDS:
            a, d = p["completeness_hi_all"][fld], p["completeness_hi_deployed"][fld]
            w.writerow([fld, HI_FIELDS.get(fld, "context"), a["present"], a["n"], d["present"], d["n"]])
    print(json.dumps({k: p[k] for k in ("n_rows", "n_columns", "n_agencies", "rows_with_id", "distinct_nonblank_ids", "deployed_plus_pilot",
                                        "high_impact", "high_impact_deployed", "high_impact_by_stage")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
