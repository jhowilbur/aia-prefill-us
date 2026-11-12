# Licences and notices

| Part | Licence |
|---|---|
| Code (`aia_us/`, `scripts/`, `tests/`) | MIT, © 2026 Jonathas Wilbur Ferreira (`LICENSE`) |
| Docs, form text structure, derived tables (`docs/`, `form/`, `reports/`, `README.md`) | CC BY 4.0, © 2026 Jonathas Wilbur Ferreira <https://creativecommons.org/licenses/by/4.0/> (the quoted memo text itself is a U.S. government work, see below) |
| Test fixtures (`tests/fixtures/`) | Fictional, written for the tests; MIT |

## OMB Memorandum M-25-21 (quoted in `form/` and `aia_us/form.py`)
OMB M-25-21, *Accelerating Federal Use of AI through Innovation, Governance, and Public Trust* (April 3, 2025).
PDF URL and SHA-256 in `data/SOURCES.csv`. A work of the U.S. Government, not subject to U.S. copyright
(17 U.S.C. § 105). The memo is quoted, not redistributed.

## 2024 and 2025 Federal Agency AI Use Case Inventories (OMB)
- 2025: https://github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory, commit
  `06c7ebeef5b376524211042bd9673b2a7fefd3e3`.
- 2024: https://github.com/ombegov/2024-Federal-AI-Use-Case-Inventory, commit
  `4a29d132291261d4829b187acd8af618e7295294`.
- Licence check (2026-11-12, GitHub API): neither repository has a LICENSE file (`license: null`).
  OMB states it compiled them from agencies' public inventories. Works prepared by U.S. federal employees
  as part of their official duties are not subject to U.S. copyright (17 U.S.C. § 105), so the inventories
  are treated as U.S. public domain. Caveats: § 105 is U.S. law only, and some free-text fields may quote
  vendor or contractor material.
- What this repository redistributes: only derived counts, categories, record indexes and agency
  use-case IDs (`reports/`). It copies no use-case names and no free text. The raw files stay in `data/raw/`
  (git-ignored) and are re-downloaded by `make data`. The 2025 CSV has a `contact_email` column
  (2,328 of 3,611 rows contain an e-mail address), and the upstream READMEs name individuals; none of
  this is copied.
- No endorsement by OMB or any agency is implied. This is independent work.
