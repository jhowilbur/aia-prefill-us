# aia-prefill-us

Open tools for the **AI impact assessment** that OMB Memorandum M-25-21 requires before a U.S. federal agency deploys high-impact AI (Appendix, Section 4(b)(ii)). There are three parts:

1. **The form.** The seven required items (A–G) as a JSON Schema and a blank Markdown template, each quoted from the memo with its page number.
2. **The checker.** `scripts/check_assessment.py` reads one filled assessment and lists what is missing or needs attention.
3. **The inventory diff.** `scripts/diff_inventories.py` compares two years of the public federal AI use-case inventory and flags status downgrades, practice fields that went from filled to blank, and cases that disappeared.

Author: Jonathas Wilbur Ferreira, Independent Researcher. It builds on [`aia-prefill-canada` v1.0.0](https://github.com/jhowilbur/aia-prefill-canada/tree/v1.0.0), the Canadian version of this work.

> **Status (v1.1.0, 2026-11-12).** Rule-based tools with unit tests on fictional fixtures. **No model is used and no accuracy is claimed.** The outputs are lists of items that are missing or need attention. **They are not a compliance rating** and do not show that any agency or system meets M-25-21.

## Quick start

Requires Python ≥ 3.10 and the standard library only. `make data` also needs `pdftotext` (poppler).

```sh
make test       # 26 unit tests on fictional fixtures, offline (one memo-quote test skips until `make data`)
make verify     # offline: form files current, checker on the three fixtures; with data: SHA-256 + reports reproduce byte for byte
make data       # download the pinned 2024 and 2025 inventories and the memo PDF into data/raw/ (git-ignored)
make reproduce  # rebuild reports/ from the pinned sources, then verify

python3 -I scripts/check_assessment.py form/assessment_template.md          # a blank form: every item listed
python3 -I scripts/check_assessment.py tests/fixtures/assessment_incomplete.md
python3 -I scripts/diff_inventories.py OLD.csv NEW.csv --out reports/diff
```

## 1. The form (`form/`)

- `form/assessment.schema.json` is a JSON Schema (draft 2020-12). Each item A–G carries the memo's wording (`x-memo-quote`) and printed page (`x-memo-page`), plus a `status` (`not started` / `in progress` / `complete`) and an `answer`. Item G also asks for the signatory's title and the signature date.
- `form/assessment_template.md` is the same form as a document to fill in.
- Both are generated from `aia_us/form.py` (`make form`). A test checks that every quote appears on its stated page of the memo's PDF text.
- The header records the high-impact status in the wording of the 2025 inventory data call, including "Presumed high-impact, but determined not high impact" and its justification.

## 2. The checker (`scripts/check_assessment.py FILE.json|FILE.md`)

It runs mechanical checks only and prints two lists, **Missing** and **Needs attention**. Exit code: 0 if nothing is listed, 1 if something is, 2 on a read error. `--json` gives machine-readable output.

| Rule | Listed when |
|---|---|
| `blank` | an item has no answer once placeholders and comments are removed |
| `placeholder` | the answer contains TBD, TODO, "[insert …]", lorem ipsum, or is only "N/A"/"Not applicable"; or a short answer (< 60 characters) says "to be determined", "see above" and similar |
| `short_answer` | the answer has fewer than 25 characters |
| `status_blank` / `status_unknown` | an item's status is missing or not one of the three allowed values |
| `in_progress` | the item's status is "in progress" or "not started", or the text says in progress, pending or "will be scheduled" |
| `duplicate` / `near_duplicate` | two items have identical answers, or answers of ≥ 30 characters with a `difflib` ratio ≥ 0.85 |
| `restates_memo` | ≥ 85 % of the answer copies the memo's own wording for that item |
| `g_signature` | item G has no signatory title, or no signature date, or the date is not a recognisable date |
| `downgrade_no_reason` | a "presumed high-impact … not high-impact" status (the form's or the 2025 inventory's wording) with no written justification |
| `header_blank` | a header field is blank |

The thresholds (0.85, 30, 25 and 60 characters) were set by the author before the checker was run on anything except the fixtures. They have not been tuned or validated on real assessments, because none are public in this format. An empty list means only that these checks found nothing. It does not mean the assessment is adequate.

## 3. The inventory diff (`scripts/diff_inventories.py OLD NEW`)

It reads the OMB 2024 and 2025 CSV formats and matches rows in this order:
1. the same agency and the same use-case ID;
2. the same agency and the same normalized name, when the name is unique on both sides;
3. a fuzzy name match within the agency (`difflib` ratio ≥ 0.90, mutual best match, no ties).

It writes these files:
- `summary.json` and `per_agency.csv` hold counts.
- `downgrades.csv`, `blanked_fields.csv` and `disappeared.csv` list cases by agency, record index and ID.

**No names or free text are written out.**

Results for 2024 → 2025 are in `reports/diff_2024_2025/` and explained in [`docs/report-v1.1.md`](docs/report-v1.1.md). Read these caveats with them:
- **The 2024 file has no use-case ID column**, so matching relies on names. 1,167 of 2,133 rows from 2024 (54.7 %) were matched.
- An unmatched row may be a renamed case, not a removed one. Rows whose agency and name repeat on either side are left unmatched rather than guessed.
- "Rights- or safety-impacting" (2024, under M-24-10) and "high-impact" (2025, under M-25-21) are different definitions. A "downgrade" between them is a prompt to look, not a finding.

## Limits

- This is not a compliance rating, not legal advice and not an official OMB tool. It certifies nothing.
- The checker tests the form of an answer, not whether it is true or sufficient.
- The inventory diff depends on how agencies named and labelled use cases, and its name matching was not checked against ground truth.
- The memo is quoted from an OCR'd PDF; quotes fix only OCR spacing (see `aia_us/form.py`).
- Reports are as of the pinned commits (2025 inventory: 2026-05-14; 2024 inventory: 2025-01-23). OMB updates the repositories on a rolling basis.

## Layout

| Folder | What |
|---|---|
| `aia_us/` | `form.py` (memo items), `checker.py`, `inventory.py` |
| `scripts/` | `build_form.py`, `check_assessment.py`, `diff_inventories.py`, `profile_inventory.py`, `fetch_inventory.py`, `verify.py` |
| `form/` | JSON Schema and Markdown template |
| `tests/` | unit tests and fictional fixtures |
| `data/SOURCES.csv` | URL, commit and SHA-256 of every source file |
| `reports/` | `profile_2025/` (2025 inventory counts), `diff_2024_2025/` |
| `docs/report-v1.1.md` | short technical report |

## Licences

Code MIT. Docs, form structure and derived tables CC BY 4.0. The memo text and the inventories are U.S. government works. See [`NOTICE.md`](NOTICE.md). This is independent work, not affiliated with or endorsed by OMB or any agency.

## Citation

See [`CITATION.cff`](CITATION.cff). The DOI will be added on publication.
