"""Rule-based checker for one filled M-25-21 Section 4(b)(ii) assessment (JSON or Markdown).

It lists what is missing or needs attention. It never grades compliance: an empty list means only
that these mechanical checks found nothing, not that the assessment is adequate.

Rules (fixed before any real assessment was seen; thresholds are documented in README):
  blank           item answer empty after removing placeholders and comments
  placeholder     answer contains a strong placeholder (TBD, TODO, lorem ipsum, [insert ...]), or a short
                  answer (< WEAK_MAX_CHARS) contains a weak one ("to be determined", "see above", ...)
  short_answer    answer shorter than SHORT_CHARS normalized characters
  status_blank / status_unknown   item status missing or not one of the allowed values
  in_progress     item status "in progress"/"not started", or text says in progress / pending
  duplicate       two items have the same normalized answer
  near_duplicate  two answers (>= MIN_CHARS) with difflib ratio >= NEAR_DUP
  restates_memo   >= NEAR_DUP of the answer's characters copy the memo wording for that item (blocks >= 8 chars)
  g_signature     item G lacks signatory title or signature date, or the date is not recognisable
  downgrade_no_reason  a "presumed high-impact ... not high-impact" status (form or 2025 inventory wording) with no justification
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from . import form as F

NEAR_DUP = 0.85
MIN_CHARS = 30
SHORT_CHARS = 25        # answers shorter than this (normalized) are listed as too short to review
WEAK_MAX_CHARS = 60     # weak placeholder phrases count only in answers shorter than this
STRONG_PLACEHOLDERS = [r"\btbd\b", r"\btbc\b", r"\btodo\b", r"lorem ipsum", r"\[(insert|fill|add)[^\]]*\]", r"\bxxx+\b",
                       r"^n/?a\.?$", r"^not applicable\.?$", r"^none\.?$", r"^-+$", r"^\?+$"]
WEAK_PLACEHOLDERS = [r"to be determined", r"to be completed", r"see above", r"same as above", r"\bplaceholder\b"]
PLACEHOLDER_RE = re.compile("|".join(STRONG_PLACEHOLDERS), re.I | re.M)
WEAK_RE = re.compile("|".join(WEAK_PLACEHOLDERS), re.I)
IN_PROGRESS_RE = re.compile(r"\bin[- ]progress\b|\bunder development\b|\bpending\b|\bwill be scheduled\b", re.I)
DATE_RE = re.compile(r"\b(19|20)\d\d-\d\d-\d\d\b|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? \d{1,2},? (19|20)\d\d\b"
                     r"|\b\d{1,2} (jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* (19|20)\d\d\b|\b\d{1,2}/\d{1,2}/(19|20)\d\d\b", re.I)


def is_placeholder(ans: str) -> bool:
    return bool(PLACEHOLDER_RE.search(ans)) or (len(ans.strip()) < WEAK_MAX_CHARS and bool(WEAK_RE.search(ans)))


def is_downgrade_status(status: str) -> bool:
    """Both the form's wording and the 2025 inventory's shorthand ("Presumed High-Impact, but Not High-impact")."""
    n = norm(status)
    return n.startswith("presumed") and "not high" in n


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()


# ---------- loading ----------
def load(path: str | Path) -> dict:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        d = json.loads(text)
        if not isinstance(d, dict):
            raise ValueError("top level must be a JSON object with 'header' and 'items'")
        return normalize_json(d)
    return parse_markdown(text)


def normalize_json(d: dict) -> dict:
    header = {k: str(v or "") for k, v in (d.get("header") or {}).items()}
    items = {}
    for iid in F.ITEM_IDS:
        it = (d.get("items") or {}).get(iid) or {}
        items[iid] = {k: str(v or "") for k, v in it.items()}
        items[iid].setdefault("status", "")
        items[iid].setdefault("answer", "")
    return {"header": header, "items": items}


def parse_markdown(text: str) -> dict:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    labels = {label.lower(): key for key, label in F.HEADER_FIELDS}
    g_labels = {label.lower(): key for key, label in F.G_EXTRA}
    header, items = {}, {iid: {"status": "", "answer": ""} for iid in F.ITEM_IDS}
    section, in_answer, buf = None, False, []

    def flush():
        if section in items:
            items[section]["answer"] = "\n".join(buf).strip()

    for line in text.splitlines():
        line = re.sub(r"^(\s*-?\s*)(\*\*|__)([^*_:]+:)(\*\*|__)", r"\1\3", line)   # **Answer:** -> Answer:
        line = re.sub(r"^(\s*-?\s*)(\*\*|__)([^*_:]+)(\*\*|__):", r"\1\3:", line)   # **Answer**: -> Answer:
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            flush()
            buf, in_answer = [], False
            h = m.group(1).strip()
            im = re.match(r"^([A-G])\.", h)
            section = im.group(1) if im else ("header" if h.lower().startswith("use case") else None)
            continue
        if section == "header":
            hm = re.match(r"^\s*-\s*([^:]+):\s*(.*)$", line)
            if hm and hm.group(1).strip().lower() in labels:
                header[labels[hm.group(1).strip().lower()]] = hm.group(2).strip()
            continue
        if section in items:
            if line.lstrip().startswith(">") and not in_answer:
                continue
            sm = re.match(r"^\s*([A-Za-z ]+):\s*(.*)$", line)
            if sm and not in_answer:
                k = sm.group(1).strip().lower()
                if k == "status":
                    items[section]["status"] = sm.group(2).strip()
                    continue
                if k in g_labels:
                    items[section][g_labels[k]] = sm.group(2).strip()
                    continue
                if k == "answer":
                    in_answer = True
                    if sm.group(2).strip():
                        buf.append(sm.group(2).strip())
                    continue
            if in_answer:
                buf.append(line)
    flush()
    return {"header": header, "items": items}


# ---------- checks ----------
def memo_overlap(ans: str, quote: str) -> float:
    """Share of the answer's characters that lie in blocks also found in the memo quote (difflib)."""
    if not ans:
        return 0.0
    sm = difflib.SequenceMatcher(None, ans, quote, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks() if b.size >= 8) / len(ans)

def strip_placeholders(s: str) -> str:
    s = PLACEHOLDER_RE.sub("", s)
    if len(s.strip()) < WEAK_MAX_CHARS:
        s = WEAK_RE.sub("", s)
    return s.strip(" \n\t.;:-")


def check(doc: dict) -> list[dict]:
    findings = []
    add = lambda rule, item, detail: findings.append({"rule": rule, "item": item, "detail": detail})
    items = doc["items"]
    for it in F.ITEMS:
        iid = it["id"]
        ans = items[iid].get("answer", "").strip()
        status = items[iid].get("status", "").strip().lower()
        if not norm(strip_placeholders(ans)):
            add("blank", iid, "no substantive answer")
        elif is_placeholder(ans):
            add("placeholder", iid, "answer contains a placeholder phrase")
        elif len(norm(ans)) < SHORT_CHARS:
            add("short_answer", iid, f"answer has fewer than {SHORT_CHARS} characters")
        if not status:
            add("status_blank", iid, "no status given")
        elif status not in F.STATUSES:
            add("status_unknown", iid, f"status '{items[iid].get('status')}' is not one of {F.STATUSES}")
        if status in ("in progress", "not started"):
            add("in_progress", iid, f"status is '{status}'")
        elif IN_PROGRESS_RE.search(ans):
            add("in_progress", iid, "answer text says the work is still in progress")
        if norm(ans) and len(norm(ans)) >= MIN_CHARS:
            r = memo_overlap(norm(ans), norm(it["quote"]))
            if r >= NEAR_DUP:
                add("restates_memo", iid, f"{r:.0%} of the answer copies the memo's wording for this item")
    g = items["G"]
    missing = [label for key, label in F.G_EXTRA if not norm(strip_placeholders(g.get(key, "")))]
    if missing:
        add("g_signature", "G", "missing: " + ", ".join(missing))
    elif not DATE_RE.search(g.get("signature_date", "")):
        add("g_signature", "G", "signature date is not a recognisable date")
    # duplicates across items
    texts = {iid: norm(items[iid].get("answer", "")) for iid in F.ITEM_IDS}
    ids = [i for i in F.ITEM_IDS if texts[i] and norm(strip_placeholders(items[i].get("answer", "")))]
    for a_i, a in enumerate(ids):
        for b in ids[a_i + 1:]:
            if texts[a] == texts[b]:
                add("duplicate", f"{a}+{b}", "identical answers")
            elif min(len(texts[a]), len(texts[b])) >= MIN_CHARS:
                r = difflib.SequenceMatcher(None, texts[a], texts[b]).ratio()
                if r >= NEAR_DUP:
                    add("near_duplicate", f"{a}+{b}", f"answers nearly identical (ratio {r:.2f})")
    h = doc["header"]
    status = h.get("high_impact_status", "").strip()
    if not status:
        add("header_blank", "header", "high-impact status is blank")
    elif is_downgrade_status(status) and not norm(strip_placeholders(h.get("high_impact_justification", ""))):
        add("downgrade_no_reason", "header", "presumed high-impact but determined not high-impact, with no written justification")
    for key, label in F.HEADER_FIELDS:
        if key in ("high_impact_status", "high_impact_justification"):
            continue
        if not h.get(key, "").strip():
            add("header_blank", "header", f"{label} is blank")
    return findings


def render(findings: list[dict], name: str) -> str:
    lines = [f"Assessment: {name}",
             "Mechanical checks only. This is not a compliance rating.", ""]
    if not findings:
        lines.append("Nothing listed by these checks (this does not mean the assessment is adequate).")
        return "\n".join(lines)
    groups = [("Missing", {"blank", "header_blank", "g_signature", "downgrade_no_reason"}),
              ("Needs attention", {"placeholder", "short_answer", "in_progress", "duplicate", "near_duplicate", "restates_memo",
                                  "status_unknown", "status_blank"})]
    for title, rules in groups:
        sel = [f for f in findings if f["rule"] in rules]
        if sel:
            lines.append(f"{title} ({len(sel)}):")
            lines += [f"  - [{f['item']}] {f['rule']}: {f['detail']}" for f in sel]
    return "\n".join(lines)
