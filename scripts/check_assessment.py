#!/usr/bin/env python3
"""List missing items and items needing attention in one filled M-25-21 4(b)(ii) assessment.

    python3 -I scripts/check_assessment.py FILE.json|FILE.md [--json]

Exit 0 if nothing is listed, 1 if something is listed, 2 on a read error. Not a compliance rating.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aia_us import checker  # noqa: E402


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        doc = checker.load(args[0])
    except (OSError, ValueError) as e:
        print(f"cannot read {args[0]}: {e}", file=sys.stderr)
        return 2
    findings = checker.check(doc)
    if "--json" in argv:
        print(json.dumps({"file": Path(args[0]).name, "not_a_compliance_rating": True, "findings": findings}, indent=2))
    else:
        print(checker.render(findings, Path(args[0]).name))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
