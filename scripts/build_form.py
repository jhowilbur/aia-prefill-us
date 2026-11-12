#!/usr/bin/env python3
"""Write form/assessment.schema.json and form/assessment_template.md from aia_us/form.py.

    python3 -I scripts/build_form.py          # write
    python3 -I scripts/build_form.py --check  # exit 1 if the files are out of date
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aia_us import form as F  # noqa: E402


def schema() -> dict:
    item_props = {}
    for it in F.ITEMS:
        props = {"status": {"type": "string", "enum": F.STATUSES},
                 "answer": {"type": "string"}}
        if it["id"] == "G":
            props.update({k: {"type": "string"} for k, _ in F.G_EXTRA})
        item_props[it["id"]] = {
            "title": f"{it['id']}. {it['title']}",
            "description": f"{F.MEMO}({it['id']}), p. {it['page']}: \"{it['quote']}\"",
            "x-memo-page": it["page"], "x-memo-quote": it["quote"],
            "type": "object", "properties": props, "required": ["status", "answer"],
            "additionalProperties": False,
        }
    header = {k: {"type": "string", "title": label} for k, label in F.HEADER_FIELDS}
    header["high_impact_status"]["enum"] = F.HIGH_IMPACT_STATUSES
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/aia-prefill-us/assessment.schema.json",
        "title": "AI impact assessment, OMB M-25-21 Section 4(b)(ii) (items A-G)",
        "description": (f"{F.MEMO}, p. {F.LEAD_IN['page']}: \"{F.LEAD_IN['quote']}\" "
                        "Structure only: filling this form does not show compliance with M-25-21."),
        "type": "object",
        "properties": {"header": {"type": "object", "properties": header,
                                  "required": ["agency", "use_case_name", "high_impact_status"]},
                       "items": {"type": "object", "properties": item_props, "required": F.ITEM_IDS,
                                 "additionalProperties": False}},
        "required": ["header", "items"],
    }


def template() -> str:
    out = ["# AI impact assessment (OMB M-25-21, Section 4(b)(ii))", "",
           f"> {F.MEMO}, p. {F.LEAD_IN['page']}: \"{F.LEAD_IN['quote']}\"", "",
           "<!-- Fill every item. Status is one of: not started | in progress | complete. "
           "This template gives structure only; it does not show compliance. -->", "",
           "## Use case", ""]
    out += [f"- {label}: " for _, label in F.HEADER_FIELDS]
    out.append("")
    for it in F.ITEMS:
        out += [f"## {it['id']}. {it['title']}", "",
                f"> p. {it['page']}: \"{it['quote']}\"", "",
                "Status: not started"]
        if it["id"] == "G":
            out += [f"{label}: " for _, label in F.G_EXTRA]
        out += ["Answer:", "", ""]
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    files = {ROOT / "form" / "assessment.schema.json": json.dumps(schema(), indent=2, ensure_ascii=False) + "\n",
             ROOT / "form" / "assessment_template.md": template()}
    if "--check" in sys.argv:
        stale = [p.name for p, t in files.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        print("stale: " + ", ".join(stale) if stale else "form files up to date")
        return 1 if stale else 0
    for p, t in files.items():
        p.parent.mkdir(exist_ok=True)
        p.write_text(t, encoding="utf-8")
        print("wrote", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
