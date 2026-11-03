"""Run with: python3 -m unittest scripts/tests/test_check_roe.py"""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import check_roe  # noqa: E402

TEMPLATE = check_roe.DEFAULT_TEMPLATE.read_text(encoding="utf-8")
ALL = {"test", "prod_like", "production"}


class CheckRoe(unittest.TestCase):
    def test_shipped_template_is_valid_for_every_kind(self):
        self.assertEqual(check_roe.validate(TEMPLATE, ALL, TEMPLATE), ([], []))

    def test_missing_kind_section(self):
        text = TEMPLATE.replace("## prod_like", "## prodlike")
        errors, _ = check_roe.validate(text, {"prod_like"})
        self.assertTrue(any("'## prod_like'" in e for e in errors))

    def test_unused_kind_is_not_required(self):
        text = TEMPLATE.replace("## production", "## something_else")
        self.assertEqual(check_roe.validate(text, {"test"})[0], [])

    def test_missing_list(self):
        text = TEMPLATE.replace("### Sandboxed\n- R-07", "### Other\n- R-07")
        errors, _ = check_roe.validate(text, {"prod_like"})
        self.assertTrue(any("'### Sandboxed'" in e for e in errors))

    def test_empty_list(self):
        text = TEMPLATE.replace("### Sandboxed\n- (none)\n\n### Forbidden\n- (none)", "### Sandboxed\n\n### Forbidden\n- (none)", 1)
        errors, _ = check_roe.validate(text, {"test"})
        self.assertTrue(any("'### Sandboxed'" in e and "empty" in e for e in errors))

    def test_rule_without_id(self):
        text = TEMPLATE.replace("- R-08 Change, overwrite", "- Change, overwrite")
        errors, _ = check_roe.validate(text, {"prod_like"})
        self.assertTrue(any("no rule ID" in e for e in errors))

    def test_duplicate_id(self):
        text = TEMPLATE.replace("- R-09 Bulk", "- R-08 Bulk")
        errors, _ = check_roe.validate(text, {"prod_like"})
        self.assertTrue(any("R-08" in e and "more than once" in e for e in errors))

    def test_modifiers_must_cover_both_settings(self):
        text = TEMPLATE.replace("allow_account_creation", "account_creation")
        errors, _ = check_roe.validate(text, {"test"})
        self.assertTrue(any("allow_account_creation" in e for e in errors))

    def test_missing_version(self):
        errors, _ = check_roe.validate(TEMPLATE.replace("rules_version: 1", ""), {"test"})
        self.assertTrue(any("rules_version" in e for e in errors))

    def test_older_file_warns(self):
        newer = TEMPLATE.replace("rules_version: 1", "rules_version: 2")
        errors, warnings = check_roe.validate(TEMPLATE, {"test"}, newer)
        self.assertEqual(errors, [])
        self.assertTrue(any("rules_version 2" in w for w in warnings))

    def test_user_may_relax_rules_without_error(self):
        text = TEMPLATE.replace("- R-13 Any state-changing action.", "- R-13 (none)")
        self.assertEqual(check_roe.validate(text, ALL)[0], [])


if __name__ == "__main__":
    unittest.main()
