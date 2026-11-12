import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aia_us import form as F  # noqa: E402

PDF_TEXT = ROOT / "data" / "raw" / "m2521.txt"


class TestForm(unittest.TestCase):
    def test_items_a_to_g(self):
        self.assertEqual(F.ITEM_IDS, list("ABCDEFG"))
        self.assertEqual([i["page"] for i in F.ITEMS], [16] * 6 + [17])

    def test_generated_files_up_to_date(self):
        r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "build_form.py"), "--check"], capture_output=True)
        self.assertEqual(r.returncode, 0, r.stdout.decode())

    def test_schema_carries_every_quote(self):
        s = json.loads((ROOT / "form" / "assessment.schema.json").read_text(encoding="utf-8"))
        props = s["properties"]["items"]["properties"]
        for it in F.ITEMS:
            self.assertEqual(props[it["id"]]["x-memo-quote"], it["quote"])
            self.assertEqual(props[it["id"]]["x-memo-page"], it["page"])

    def test_template_has_every_item(self):
        t = (ROOT / "form" / "assessment_template.md").read_text(encoding="utf-8")
        for it in F.ITEMS:
            self.assertIn(f"## {it['id']}. {it['title']}", t)
            self.assertIn(it["quote"], t)

    @unittest.skipUnless(PDF_TEXT.exists(), "run `make data` to extract the memo text")
    def test_quotes_on_stated_pdf_page(self):
        pages = PDF_TEXT.read_text(encoding="utf-8").split("\f")
        sq = lambda s: re.sub(r"\s+", "", s)
        for q, p in [(F.LEAD_IN["quote"], F.LEAD_IN["page"])] + [(i["quote"], i["page"]) for i in F.ITEMS]:
            self.assertIn(sq(q), sq(pages[p - 1]), f"quote not found on page {p}: {q[:40]}")


if __name__ == "__main__":
    unittest.main()
