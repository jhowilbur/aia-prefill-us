#!/usr/bin/env python3
"""Compare two federal AI use-case inventories (OMB 2024 or 2025 CSV format).

    python3 -I scripts/diff_inventories.py OLD.csv NEW.csv [--out DIR]

Writes DIR/summary.json, per_agency.csv, downgrades.csv, blanked_fields.csv, disappeared.csv
(default DIR: reports/diff). Outputs carry agencies, record indexes, IDs and categories only:
no names or free text. A flag is a prompt to look, not a finding of non-compliance.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aia_us import inventory as I  # noqa: E402


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str]) -> int:
    out = ROOT / "reports" / "diff"
    if "--out" in argv:
        i = argv.index("--out")
        out = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    res = I.diff(I.load(argv[0]), I.load(argv[1]))
    res["summary"]["old_file"], res["summary"]["new_file"] = Path(argv[0]).name, Path(argv[1]).name
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(res["summary"], indent=2) + "\n", encoding="utf-8")
    write_csv(out / "per_agency.csv", res["per_agency"], list(res["per_agency"][0]) if res["per_agency"] else ["agency"])
    write_csv(out / "downgrades.csv", res["downgrades"], ["agency", "old_row", "old_id", "new_row", "new_id", "new_hi",
                                                         "new_justification_present", "match_method"])
    write_csv(out / "blanked_fields.csv", res["blanked"], ["agency", "old_row", "new_row", "new_id", "field", "new_hi",
                                                           "new_stage", "match_method"])
    write_csv(out / "disappeared.csv", res["disappeared"], ["agency", "old_row", "old_id", "old_hi"])
    s = res["summary"]
    print(json.dumps({k: s[k] for k in ("old_rows", "new_rows", "old_rows_with_id", "matched", "match_methods",
                                        "match_rate_old", "old_high", "old_high_matched", "downgraded",
                                        "downgraded_by_new_category", "blanked_cases", "blanked_cases_new_high_deployed",
                                        "disappeared", "disappeared_old_high")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
