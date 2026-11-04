import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "trigger action" / "trigger_action.py"
spec = importlib.util.spec_from_file_location("trigger_action", SCRIPT_PATH)
automation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(automation)


class AutomationTests(unittest.TestCase):
    def test_diff_is_bounded_before_concatenation(self):
        files = [SimpleNamespace(filename="large.py", patch="x" * 100000)]
        diff, changed = automation.collect_diff(files, 1000)
        self.assertLessEqual(len(diff), 1000)
        self.assertEqual(changed, ["large.py"])
        self.assertIn("[Diff truncated...]", diff)

    def test_diff_limit_with_oversized_filename(self):
        files = [SimpleNamespace(filename="x" * 5000, patch="patch")]
        diff, _ = automation.collect_diff(files, 100)
        self.assertLessEqual(len(diff), 100)

    def test_model_output_is_validated_and_file_is_constrained(self):
        result = automation.validate_result(
            {
                "issue_title": "Title",
                "issue_body": "Body",
                "summary": "Summary",
                "affected_file": "../../etc/passwd",
                "affected_line": -5,
                "labels": ["security"],
                "severity": "HIGH",
            },
            ["api/index.py"],
        )
        self.assertEqual(result["affected_file"], "")
        self.assertEqual(result["affected_line"], 1)
        self.assertEqual(result["severity"], "high")
        with self.assertRaises(ValueError):
            automation.validate_result(
                {"issue_title": "Title", "issue_body": "Body", "summary": 1}, []
            )

    def test_empty_closed_title_does_not_match_every_issue(self):
        self.assertFalse(automation.closed_issue_exists(None, "owner/repo", ""))

    def test_change_detection(self):
        self.assertEqual(automation.detect_change_type(["api/index.py"]), "backend")
        self.assertEqual(automation.detect_change_type(["app.js", "styles.css"]), "frontend")
        self.assertEqual(automation.detect_change_type([".github/workflows/lint.yml"]), "ci")
        self.assertEqual(automation.detect_change_type(["README.md"]), "docs")


if __name__ == "__main__":
    unittest.main()
