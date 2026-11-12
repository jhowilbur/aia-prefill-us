# aia-prefill-us v1.1.0: technical report

Jonathas Wilbur Ferreira, Independent Researcher. 2026-11-12.

**Not a compliance rating.** Nothing here measures whether an agency or system meets OMB M-25-21. No model is used and no accuracy is claimed.

Each number is tagged **[M]** (measured by a command in this repository), **[R]** (read from a source document) or **[D]** (derived by the arithmetic shown). The command that produces each [M] number is given in its section. All of them run offline once `make data` has downloaded the pinned files.

## 1. Sources (pinned)

| File | Commit / URL | SHA-256 (first 12) |
|---|---|---|
| 2025 inventory, `2025_individually_reported_AI_use_cases.csv` | ombegov/2025-Federal-Agency-AI-Use-Case-Inventory @ `06c7ebe` | `a62721202ca4` |
| 2024 inventory, `2024_consolidated_ai_inventory_raw_v2.csv` | ombegov/2024-Federal-AI-Use-Case-Inventory @ `4a29d13` | `789e1bac6d25` |
| OMB M-25-21 PDF | whitehouse.gov (full URL in `data/SOURCES.csv`) | `0aab0aa4eaea` |

The full hashes are in `data/SOURCES.csv`; check them with `make verify`. The M-25-21 hash matches the one recorded in v1.0.0 (`0aab0aa4…9813`) [M].

## 2. The form

- The seven items of M-25-21 Appendix § 4(b)(ii) and their lead-in are quoted in `aia_us/form.py`.
  - Items A–F and the lead-in are on printed page 16; item G is on page 17 [R].
  - All 8 quotes appear, ignoring whitespace, on the stated page of `pdftotext -layout` output [M: `make test`, test `test_quotes_on_stated_pdf_page`].
- The checker's results on the three fictional fixtures [M: `make verify`]:

| Fixture | Exit | Items listed |
|---|---|---|
| `assessment_good.json` | 0 | 0 |
| `assessment_incomplete.md` | 1 | 10: C, D, E blank; G signature missing; downgrade with no reason; assessment date blank; B and G too short; B in progress; C not started |
| `assessment_boilerplate.json` | 1 | 7: 3 identical pairs, 3 near-identical pairs, D copies the memo wording |

These show the rules fire as written. They say nothing about how often the rules are right on real assessments, because no real assessments in this format are public.

## 3. The 2025 inventory: dataset profile

Command: `python3 -I scripts/profile_inventory.py --out reports/profile_2025`; numbers from `reports/profile_2025/inventory_profile.json`.

| Quantity | Value |
|---|---|
| Rows, columns, agencies | 3,611, 36, 41 [M] (README: 3,611 use cases, 41 agency submissions [R]) |
| High-impact | 445 [M] (README: 445 [R]) |
| High-impact by stage | 227 deployed, 140 pre-deployment, 55 retired, 23 pilot [M] |
| Deployed + pilot | 1,480 [M], plus 338 rows with a blank stage (DOC 223, TVA 59, ED 56) [M]. 1,480 + 338 = 1,818 [D], the README's "deployed and piloted" total [R] |
| Rows with a use-case ID | 2,907 [M] (704 rows have none: 3,611 − 704 = 2,907 [D]); 2,892 distinct IDs [M], so 2,907 − 2,892 = 15 rows reuse an ID [D] |

Practice fields answered, among the 227 deployed high-impact cases [M, `reports/profile_2025/hi_field_completeness.csv`]:
- **Filled:** 125 or 126 of 227 for each of the seven 4(b) practice fields.
- **Blank:** 101 or 102 of 227.
- **"Yes" answers:**
  - impact assessment completed: 36;
  - pre-deployment testing: 44;
  - appeal process established: 16.

## 4. 2024 → 2025 inventory diff

Command: `python3 -I scripts/diff_inventories.py data/raw/2024_consolidated_ai_inventory_raw_v2.csv data/raw/2025_individually_reported_AI_use_cases.csv --out reports/diff_2024_2025`. Numbers come from `reports/diff_2024_2025/summary.json` and `per_agency.csv` [M].

**Matching.**
- The 2024 file has **no use-case ID column** [M], so no row could be matched on ID.
- Before names are compared, a cross-reference that some agencies append to the 2025 name (for example "[2024 INV#…]") is removed.
- 1,167 of 2,133 rows from 2024 were matched: 1,121 on exact names and 46 on fuzzy names.
  - Match rate on the 2024 side: 0.547 [M].
  - On the 2025 side: 1,167 / 3,611 = 0.323 [D].
- Matching precision has no ground truth. The independent spot check (section 6) found no clear errors in its sample.
- Recall is the weak side. 41 unmatched 2024 rows (12 of them rights/safety-impacting) have an identical agency and name in 2025 [M]. They stay unmatched because that name repeats on one side, and the tool does not guess between repeats.

**Status changes.**
- The 2024 file has 351 rows that are rights- and/or safety-impacting [M] (README: 351 [R]); 216 of them were matched [M].
- 29 matched rows went from rights/safety-impacting (2024) to a non-high-impact category in 2025 [M]:
  - 17 to "Not high-impact";
  - 12 to "Presumed high-impact, but determined not high-impact", all 12 with a written justification.
  - By agency: DOJ 15, VA 7, HHS 3, DHS 1, DOL 1, HUD 1, SSA 1.
  - All 29 were matched on exact names [M].
- The two categories come from different memos (M-24-10 in 2024, M-25-21 in 2025), so a change is a prompt to look, not evidence of an improper downgrade.

**Filled → blank.**
- 86 matched cases had at least one practice field that was filled in 2024 and blank in 2025: 473 field instances [M].
- Only 4 of those cases are high-impact and deployed in 2025, the only cases for which the 2025 data call requires the fields [M] [R: 2025 data dictionary]. The rest are expected blanks under the 2025 rules.

**Unmatched 2024 rows ("disappeared").**
- 966 rows [M], 135 of them rights/safety-impacting [M]: DOJ 59, VA 41, USAID 17, DHS 5, DOE 3, TREAS 2, SSA 2, OPM 2, others ≤ 1.
- Some were renamed, some fell out of scope under the 2025 rules (R&D scope, COTS consolidated reporting [R: 2025 README]), and some agencies did not report in 2025 (e.g. USAID).

## 5. Tests

`make test`: 26 tests, all pass [M]. Two fixes were reverted to confirm the tests catch them [M]:
- When `[]` was no longer treated as blank, 2 tests failed.
- When the downgrade rule accepted only the form's own wording, `test_review_false_negatives` failed.

Both passed again once the fixes were restored [M].

## 6. Independent review

A separate reviewer agent was given the folder and the raw files, not this report's conclusions, on 2026-11-12. It re-derived the counts with its own code and tried to break the checker.

**Confirmed by the reviewer** [M, its own run]:
- The memo quotes are word for word, on the right pages, and nothing in § 4(b)(ii) is left out.
- All 2025 and 2024 counts in section 3, and the 2024 rights/safety total.
- The 2024 file has no ID column.
- The diff outputs reproduce byte for byte.
- In a seeded sample of 30 exact-name pairs, 30 were correct. Of the 40 fuzzy pairs (pre-fix run), none was clearly wrong and 3 were uncertain.
- 10 of the 29 downgrade rows, checked by hand in the raw files, were all correct.
- `make test` and `make verify` pass.
- The personal-data scan found nothing beyond the author's own name and the reserved `example.invalid` addresses in the fixtures.

**Found and fixed:**
1. The cross-reference suffix on 2025 names blocked matches, for example at DOI (8 of 180 rows matched before, 85 after).
2. The checker missed:
   - one-word answers (new `short_answer` rule, < 25 characters);
   - a missing status (`status_blank`);
   - "Not applicable." as a whole answer;
   - "pending" and "will be scheduled";
   - a signature date that is not a date;
   - the 2025 inventory's own wording of the downgrade status.
3. Legitimate long answers containing "to be completed" were flagged; weak phrases now count only in answers under 60 characters.
4. Bold Markdown labels (`**Answer:**`) were not read.
5. A JSON file whose top level is a list exited 1 instead of 2.
6. `unique_ids` counted the blank ID.

Each fix has a regression test.

**Kept as limits, not fixed:**
- Rows whose names repeat stay unmatched (counted in section 4).
- The word "downgrade" is kept in file names; the reviewer suggested "category change" because the 2024 and 2025 definitions differ. The caveat is in the README and section 4.
- Item C's quote omits footnote 30 (the E-Government Act § 208 and M-03-22 privacy reference).

## 7. Limits

- The tool assists human reviewers. It is not a compliance rating and certifies nothing.
- The checker's thresholds were not validated on real assessments.
- The inventory diff relies on names, because 2024 has no IDs. Renamed cases and repeated names count as disappeared, and agencies' own 2024 files (which may carry IDs) were not used.
- The checker's phrase lists are English-only and short, and it cannot tell a true answer from a false one.
- The 2024 and 2025 status categories are defined by different memos.
- The data reflect the pinned commits and whatever agencies chose to publish.
