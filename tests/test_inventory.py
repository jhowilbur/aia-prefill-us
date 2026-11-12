import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT))
from aia_us import inventory as I  # noqa: E402


class TestInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.y24 = I.load(FX / "inventory_2024_fixture.csv")
        cls.y25 = I.load(FX / "inventory_2025_fixture.csv")
        cls.y26 = I.load(FX / "inventory_2026_fixture.csv")

    def test_formats_and_cp1252(self):
        self.assertEqual((self.y24["format"], self.y25["format"]), ("2024", "2025"))
        self.assertTrue(any("caf" in r["name"] for r in self.y24["records"]))

    def test_categories(self):
        self.assertEqual([r["hi"] for r in self.y24["records"]][:5], ["high", "high", "not", "not", "high"])
        self.assertEqual(self.y25["records"][1]["hi"], "presumed_not")

    def test_empty_list_is_blank(self):
        self.assertEqual(self.y25["records"][0]["practice"]["consultation"], "blank")

    def test_xref_suffix_stripped(self):
        self.assertEqual(I.norm_name("Stream Gauge Model [2024 INV#XYZ-62]"), I.norm_name("Stream gauge model"))

    def test_name_matching_2024_2025(self):
        p = I.match(self.y24["records"], self.y25["records"])
        self.assertEqual(p[1], (1, "exact_name"))
        self.assertEqual(p[2], (2, "fuzzy_name"))      # "(MS)" dropped in 2025
        self.assertNotIn(3, p)                         # ambiguous duplicate names stay unmatched
        self.assertNotIn(4, p)
        self.assertEqual(p[7][1], "fuzzy_name")        # accent / curly quotes

    def test_diff_2024_2025(self):
        r = I.diff(self.y24, self.y25)
        s = r["summary"]
        self.assertEqual((s["old_rows"], s["matched"], s["old_rows_with_id"]), (7, 4, 0))
        self.assertEqual([(d["old_row"], d["new_hi"], d["new_justification_present"]) for d in r["downgrades"]],
                         [(2, "presumed_not", False)])
        self.assertIn((1, "consultation"), {(b["old_row"], b["field"]) for b in r["blanked"]})
        self.assertIn((1, "risks_or_impacts"), {(b["old_row"], b["field"]) for b in r["blanked"]})
        self.assertNotIn((6, "impact_assessment"), {(b["old_row"], b["field"]) for b in r["blanked"]})  # N/A is not "filled"
        self.assertEqual(sorted(d["old_row"] for d in r["disappeared"]), [3, 4, 5])

    def test_id_matching_same_format(self):
        r = I.diff(self.y25, self.y26)
        self.assertEqual(r["summary"]["match_methods"].get("id"), 5)
        self.assertEqual([(d["new_id"], d["new_hi"]) for d in r["downgrades"]], [("EXA-1", "not")])
        self.assertIn(("EXA-1", "monitoring"), {(b["new_id"], b["field"]) for b in r["blanked"]})
        self.assertEqual([d["old_id"] for d in r["disappeared"]], ["TST-11"])

    def test_cli_writes_no_names_or_emails(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "diff_inventories.py"),
                            str(FX / "inventory_2024_fixture.csv"), str(FX / "inventory_2025_fixture.csv"), "--out", d],
                           check=True, capture_output=True)
            out = "".join(p.read_text(encoding="utf-8") for p in Path(d).iterdir())
            for leak in ("Fictional", "example.invalid", "risk text", "Claims Triage"):
                self.assertNotIn(leak, out)
            self.assertEqual(json.loads((Path(d) / "summary.json").read_text())["matched"], 4)


if __name__ == "__main__":
    unittest.main()
