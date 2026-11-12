"""Load a federal AI use-case inventory CSV (2024 or 2025 OMB format) and diff two years.

Only structured fields are kept in memory as outputs: agency, record index, use-case ID,
high-impact category, stage and filled/blank flags. Use-case names are used for matching only
and never written out. Record index = 1-based position of the data record in the file
(not the text line number; records can span lines).
"""
from __future__ import annotations

import csv
import difflib
import io
import re
from collections import Counter, defaultdict
from pathlib import Path

BLANK = {"", "[]", "nan", "null"}
NOT_APPLICABLE = {"n/a", "na", "not applicable", "none", "[]"}
FUZZY_MIN = 0.90
FUZZY_MIN_CHARS = 10

# canonical practice field -> (2024 header prefix, 2025 column)
PRACTICES = {
    "impact_assessment": ("Has an AI impact assessment been conducted", "hi_assessment_completed"),
    "testing": ("Has the AI use case been tested in operational", "hi_testing_conducted"),
    "risks_or_impacts": ("What are the key risks from using the AI", "hi_potential_impacts"),
    "independent_review": ("Has an independent evaluation of the AI use case", "hi_independent_review"),
    "monitoring": ("Is there a process to monitor performance", "hi_ongoing_monitoring"),
    "consultation": ("What steps has the agency taken to consult", "hi_public_consultation"),
    "appeal": ("Is there an established fallback and escalation process", "hi_appeal_process"),
}
HI_2024 = "Is the AI use case rights-impacting, safety-impacting"


# Some agencies append a cross-reference to last year's entry to the 2025 name, e.g. "... [2024 INV#XYZ-62]".
XREF_RE = re.compile(r"\[\s*20\d\d\s*inv[^\]]*\]", re.I)


def norm_name(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", XREF_RE.sub(" ", s).lower()).strip()


def read_csv(path: str | Path) -> tuple[list[str], list[dict]]:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"cannot decode {path}")
    rd = csv.DictReader(io.StringIO(text, newline=""))
    return list(rd.fieldnames or []), list(rd)


def detect(header: list[str]) -> str:
    if "is_high_impact" in header and "agency" in header:
        return "2025"
    if "Use Case Name" in header and "Agency Abbreviation" in header:
        return "2024"
    raise ValueError("unknown inventory format")


def hi_category(fmt: str, v: str) -> str:
    s = v.strip().lower()
    if fmt == "2025":
        if not s:
            return "blank"
        if s.startswith("presumed") or "determined not" in s:
            return "presumed_not"
        if "not high" in s:
            return "not"
        if "high-impact" in s or "high impact" in s:
            return "high"
        return "other"
    if not s:
        return "blank"
    if s in ("both", "rights-impacting", "safety-impacting"):
        return "high"
    if s == "neither":
        return "not"
    return "other"


def filled(v: str | None) -> str:
    s = (v or "").strip().lower()
    if s in BLANK:
        return "blank"
    if s in NOT_APPLICABLE:
        return "na"
    return "filled"


def load(path: str | Path) -> dict:
    header, rows = read_csv(path)
    fmt = detect(header)
    cols = {}
    for k, (p24, c25) in PRACTICES.items():
        if fmt == "2025":
            cols[k] = c25 if c25 in header else None
        else:
            cols[k] = next((h for h in header if h.startswith(p24)), None)
    hi_col = "is_high_impact" if fmt == "2025" else next((h for h in header if h.startswith(HI_2024)), None)
    recs = []
    for i, r in enumerate(rows, 1):
        g = lambda c: (r.get(c) or "") if c else ""
        recs.append({
            "row": i,
            "agency": g("agency" if fmt == "2025" else "Agency Abbreviation").strip(),
            "id": g("id").strip() if fmt == "2025" else "",
            "name": norm_name(g("use_case_name" if fmt == "2025" else "Use Case Name")),
            "hi": hi_category(fmt, g(hi_col)),
            "justification": filled(g("HI_justification")) == "filled" if fmt == "2025" else False,
            "stage": g("development_stage" if fmt == "2025" else "Stage of Development").strip(),
            "practice": {k: filled(g(c)) if c else "absent" for k, c in cols.items()},
        })
    return {"format": fmt, "records": recs, "practice_columns": {k: bool(c) for k, c in cols.items()}}


def match(old: list[dict], new: list[dict]) -> dict[int, tuple[int, str]]:
    """old row -> (new row, method). Methods in order: id, exact_name, fuzzy_name. One-to-one."""
    pairs: dict[int, tuple[int, str]] = {}
    used_new: set[int] = set()

    def unique_index(recs, keyf):
        c = Counter(keyf(r) for r in recs)
        return {keyf(r): r["row"] for r in recs if keyf(r)[1] and c[keyf(r)] == 1}

    for method, keyf in (("id", lambda r: (r["agency"], r["id"])), ("exact_name", lambda r: (r["agency"], r["name"]))):
        o = unique_index([r for r in old if r["row"] not in pairs], keyf)
        n = unique_index([r for r in new if r["row"] not in used_new], keyf)
        for k, orow in sorted(o.items(), key=lambda kv: kv[1]):
            if k in n:
                pairs[orow] = (n[k], method)
                used_new.add(n[k])
    # fuzzy, within agency, mutual best with a unique best
    by_ag_old, by_ag_new = defaultdict(list), defaultdict(list)
    for r in old:
        if r["row"] not in pairs and len(r["name"]) >= FUZZY_MIN_CHARS:
            by_ag_old[r["agency"]].append(r)
    for r in new:
        if r["row"] not in used_new and len(r["name"]) >= FUZZY_MIN_CHARS:
            by_ag_new[r["agency"]].append(r)
    for ag in sorted(by_ag_old):
        O, N = by_ag_old[ag], by_ag_new.get(ag, [])
        if not N:
            continue
        score = {}
        for o in O:
            for n in N:
                score[(o["row"], n["row"])] = difflib.SequenceMatcher(None, o["name"], n["name"], autojunk=False).ratio()
        def best(keys):
            ks = sorted(keys, key=lambda k: -score[k])
            if not ks or score[ks[0]] < FUZZY_MIN:
                return None
            if len(ks) > 1 and score[ks[1]] == score[ks[0]]:
                return None
            return ks[0]
        for o in O:
            b = best([(o["row"], n["row"]) for n in N])
            if not b:
                continue
            back = best([(oo["row"], b[1]) for oo in O])
            if back == b and b[1] not in used_new:
                pairs[o["row"]] = (b[1], "fuzzy_name")
                used_new.add(b[1])
    return pairs


def diff(old_inv: dict, new_inv: dict) -> dict:
    old, new = old_inv["records"], new_inv["records"]
    nmap = {r["row"]: r for r in new}
    pairs = match(old, new)
    downgrades, blanked, disappeared = [], [], []
    for o in old:
        if o["row"] not in pairs:
            disappeared.append({"agency": o["agency"], "old_row": o["row"], "old_id": o["id"], "old_hi": o["hi"]})
            continue
        nrow, method = pairs[o["row"]]
        n = nmap[nrow]
        if o["hi"] == "high" and n["hi"] in ("not", "presumed_not", "blank"):
            downgrades.append({"agency": o["agency"], "old_row": o["row"], "old_id": o["id"], "new_row": nrow,
                               "new_id": n["id"], "new_hi": n["hi"], "new_justification_present": n["justification"],
                               "match_method": method})
        for k in PRACTICES:
            if o["practice"].get(k) == "filled" and n["practice"].get(k) == "blank":
                blanked.append({"agency": o["agency"], "old_row": o["row"], "new_row": nrow, "new_id": n["id"],
                                "field": k, "new_hi": n["hi"], "new_stage": n["stage"], "match_method": method})
    methods = Counter(m for _, m in pairs.values())
    agencies = sorted({r["agency"] for r in old} | {r["agency"] for r in new})
    per_agency = []
    for ag in agencies:
        o_n = sum(r["agency"] == ag for r in old)
        m_n = sum(1 for r in old if r["agency"] == ag and r["row"] in pairs)
        per_agency.append({
            "agency": ag, "old_rows": o_n, "new_rows": sum(r["agency"] == ag for r in new), "matched": m_n,
            "match_rate_old": round(m_n / o_n, 3) if o_n else "",
            "old_high": sum(r["agency"] == ag and r["hi"] == "high" for r in old),
            "new_high": sum(r["agency"] == ag and r["hi"] == "high" for r in new),
            "downgraded": sum(d["agency"] == ag for d in downgrades),
            "blanked_field_cases": len({b["old_row"] for b in blanked if b["agency"] == ag}),
            "disappeared": sum(d["agency"] == ag for d in disappeared),
            "disappeared_old_high": sum(d["agency"] == ag and d["old_hi"] == "high" for d in disappeared),
        })
    old_high = [r for r in old if r["hi"] == "high"]
    summary = {
        "old_format": old_inv["format"], "new_format": new_inv["format"],
        "old_rows": len(old), "new_rows": len(new),
        "old_rows_with_id": sum(bool(r["id"]) for r in old), "new_rows_with_id": sum(bool(r["id"]) for r in new),
        "matched": len(pairs), "match_methods": dict(methods),
        "match_rate_old": round(len(pairs) / len(old), 4) if old else None,
        "match_rate_new": round(len(pairs) / len(new), 4) if new else None,
        "old_hi_categories": dict(Counter(r["hi"] for r in old)),
        "new_hi_categories": dict(Counter(r["hi"] for r in new)),
        "old_high": len(old_high),
        "old_high_matched": sum(r["row"] in pairs for r in old_high),
        "downgraded": len(downgrades),
        "downgraded_by_new_category": dict(Counter(d["new_hi"] for d in downgrades)),
        "downgraded_presumed_not_without_justification": sum(d["new_hi"] == "presumed_not" and not d["new_justification_present"] for d in downgrades),
        "blanked_field_instances": len(blanked),
        "blanked_cases": len({b["old_row"] for b in blanked}),
        "blanked_by_field": dict(Counter(b["field"] for b in blanked)),
        "blanked_cases_new_high_deployed": len({b["old_row"] for b in blanked if b["new_hi"] == "high" and b["new_stage"] == "Deployed"}),
        "disappeared": len(disappeared),
        "disappeared_old_high": sum(d["old_hi"] == "high" for d in disappeared),
        "practice_columns_old": old_inv["practice_columns"], "practice_columns_new": new_inv["practice_columns"],
        "params": {"fuzzy_min_ratio": FUZZY_MIN, "fuzzy_min_chars": FUZZY_MIN_CHARS},
    }
    return {"summary": summary, "per_agency": per_agency, "downgrades": downgrades,
            "blanked": blanked, "disappeared": disappeared}
