"""Run with: python3 -m unittest scripts/tests/test_build_runner_agents.py"""
import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import build_runner_agents as b  # noqa: E402


def tools_of(text):
    return re.search(r"^tools: (.*)$", text, re.M).group(1)


class RunnerAgents(unittest.TestCase):
    def test_files_on_disk_are_up_to_date(self):
        for name in b.VARIANTS:
            path = b.AGENTS / f"session-runner-{name}.md"
            self.assertTrue(path.exists(), path)
            self.assertEqual(path.read_text(encoding="utf-8"), b.render(name), f"{path.name} is stale: run scripts/build_runner_agents.py")

    def test_each_runner_has_only_its_servers(self):
        mobile, web, both = (tools_of(b.render(n)) for n in ("mobile", "web", "mobile-web"))
        self.assertIn("appium", mobile)
        self.assertIn("xcodebuild", mobile)
        self.assertNotIn("playwright", mobile)
        self.assertIn("playwright", web)
        self.assertNotIn("appium", web)
        self.assertNotIn("xcodebuild", web)
        for server in ("appium", "xcodebuild", "playwright"):
            self.assertIn(server, both)

    def test_no_old_generic_runner_left(self):
        self.assertFalse((b.AGENTS / "session-runner.md").exists())


if __name__ == "__main__":
    unittest.main()
