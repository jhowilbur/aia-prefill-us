import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT))
from aia_us import checker as C  # noqa: E402


def rules(findings, item=None):
    return {f["rule"] for f in findings if item is None or f["item"] == item}


class TestChecker(unittest.TestCase):
    def test_good_lists_nothing(self):
        self.assertEqual(C.check(C.load(FX / "assessment_good.json")), [])

    def test_incomplete(self):
        f = C.check(C.load(FX / "assessment_incomplete.md"))
        self.assertIn("blank", rules(f, "C"))
        self.assertIn("blank", rules(f, "D"))      # "TBD" only
        self.assertIn("blank", rules(f, "E"))      # "[insert ...]" only
        self.assertIn("in_progress", rules(f, "B"))
        self.assertIn("g_signature", rules(f, "G"))
        self.assertIn("downgrade_no_reason", rules(f, "header"))
        self.assertNotIn("blank", rules(f, "A"))

    def test_boilerplate(self):
        f = C.check(C.load(FX / "assessment_boilerplate.json"))
        self.assertIn("duplicate", rules(f, "A+B"))
        self.assertIn("near_duplicate", rules(f, "A+C"))
        self.assertIn("restates_memo", rules(f, "D"))
        self.assertNotIn("restates_memo", rules(f, "E"))

    def test_blank_template_lists_all_items(self):
        f = C.check(C.load(ROOT / "form" / "assessment_template.md"))
        self.assertEqual({x["item"] for x in f if x["rule"] == "blank"}, set("ABCDEFG"))

    def test_downgrade_with_reason_not_flagged(self):
        d = C.load(FX / "assessment_good.json")
        d["header"]["high_impact_status"] = "Presumed high-impact, but determined not high impact"
        self.assertIn("downgrade_no_reason", rules(C.check(d), "header"))
        d["header"]["high_impact_justification"] = "Output is advisory and reviewed in full by staff before any action."
        self.assertNotIn("downgrade_no_reason", rules(C.check(d), "header"))

    def test_placeholder_inside_text(self):
        d = C.load(FX / "assessment_good.json")
        d["items"]["E"]["answer"] = "Direct costs TBD after the contract is awarded."
        self.assertIn("placeholder", rules(C.check(d), "E"))

    def test_in_progress_from_text(self):
        d = C.load(FX / "assessment_good.json")
        d["items"]["F"]["answer"] = "Independent review is in progress with the evaluation office."
        self.assertIn("in_progress", rules(C.check(d), "F"))

    def test_markdown_and_json_agree(self):
        d = C.load(FX / "assessment_good.json")
        lines = ["## Use case", ""] + [f"- {label}: {d['header'].get(k, '')}" for k, label in C.F.HEADER_FIELDS]
        for it in C.F.ITEMS:
            x = d["items"][it["id"]]
            lines += ["", f"## {it['id']}. {it['title']}", f"> p. {it['page']}: quote", f"Status: {x['status']}"]
            if it["id"] == "G":
                lines += [f"Signatory title: {x['signatory_title']}", f"Signature date: {x['signature_date']}"]
            lines += ["Answer:", x["answer"]]
        md = C.parse_markdown("\n".join(lines))
        for iid in C.F.ITEM_IDS:
            self.assertEqual(md["items"][iid]["answer"], d["items"][iid]["answer"])
        self.assertEqual(C.check(md), [])

    def test_cli_exit_codes_and_disclaimer(self):
        run = lambda p: subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "check_assessment.py"), str(p)],
                                       capture_output=True, text=True)
        good, bad = run(FX / "assessment_good.json"), run(FX / "assessment_incomplete.md")
        self.assertEqual((good.returncode, bad.returncode), (0, 1))
        self.assertIn("not a compliance rating", good.stdout)
        self.assertNotRegex(good.stdout + bad.stdout, r"(?i)\b(score|grade|compliant|pass(ed)?)\b")

    # regressions from the independent review (2026-11-12)
    def test_review_false_negatives(self):
        d = C.load(FX / "assessment_good.json")
        d["items"]["A"]["answer"] = "Yes."
        d["items"]["B"]["status"] = ""
        d["items"]["E"]["answer"] = "Not applicable."
        d["items"]["F"]["answer"] = "An independent review will be scheduled after deployment; results pending."
        d["items"]["G"]["signature_date"] = "soon"
        d["header"]["high_impact_status"] = "Presumed High-Impact, but Not High-impact"   # 2025 inventory wording
        f = C.check(d)
        self.assertIn("short_answer", rules(f, "A"))
        self.assertIn("status_blank", rules(f, "B"))
        self.assertIn("blank", rules(f, "E"))
        self.assertIn("in_progress", rules(f, "F"))
        self.assertIn("g_signature", rules(f, "G"))
        self.assertIn("downgrade_no_reason", rules(f, "header"))

    def test_review_false_positive_long_answer(self):
        d = C.load(FX / "assessment_good.json")
        d["items"]["D"]["answer"] = ("Reassessment is to be completed every 12 months and after any retraining; "
                                     "the schedule is kept in the system's change log.")
        self.assertEqual(rules(C.check(d), "D"), set())

    def test_bold_markdown_labels(self):
        md = C.parse_markdown("## A. Purpose\n**Status:** complete\n**Answer:**\nSorts mail into twelve routing categories.")
        self.assertEqual(md["items"]["A"]["status"], "complete")
        self.assertTrue(md["items"]["A"]["answer"].startswith("Sorts mail"))

    def test_json_list_is_read_error(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
            t.write("[]")
        r = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "check_assessment.py"), t.name], capture_output=True)
        Path(t.name).unlink()
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
