# Requires Python >= 3.10 (standard library only). `make data` also needs pdftotext (poppler)
# to extract the memo text used by one test.
PY = python3 -I
RAW = data/raw

.PHONY: verify test data reproduce form clean-data

verify:     ## offline: form files current, checker on fixtures; data checks too once `make data` has run
	$(PY) scripts/verify.py

test:       ## unit tests on fictional fixtures (offline; one memo-quote test skips until `make data`)
	$(PY) -m unittest discover -s tests -t .

data:       ## download the pinned inventories and M-25-21 into data/raw/ (git-ignored), check SHA-256
	$(PY) scripts/fetch_inventory.py
	pdftotext -layout $(RAW)/M-25-21.pdf $(RAW)/m2521.txt

form:       ## regenerate form/assessment.schema.json and form/assessment_template.md
	$(PY) scripts/build_form.py

reproduce: data   ## rebuild every report from the pinned sources
	$(PY) scripts/profile_inventory.py --out reports/profile_2025
	$(PY) scripts/diff_inventories.py $(RAW)/2024_consolidated_ai_inventory_raw_v2.csv \
	  $(RAW)/2025_individually_reported_AI_use_cases.csv --out reports/diff_2024_2025
	$(PY) scripts/verify.py

clean-data:
	rm -rf $(RAW)
