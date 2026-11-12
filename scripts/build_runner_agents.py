#!/usr/bin/env python3
"""Generate the session-runner agent files from one template.

A plugin agent cannot change its own tool list per spawn, and every tool schema in an agent's
tool list is re-read on every turn. So there is one Runner per kind of target, each with only the
MCP servers it needs, and all of them share one body (scripts/runner-agent/template.md).

    python3 scripts/build_runner_agents.py          # write agents/session-runner-*.md
    python3 scripts/build_runner_agents.py --check  # exit 1 if the files on disk are out of date

"mobile-web" means a session that uses BOTH a mobile app and a web app (for example a customer
creates a request in the mobile app and an admin approves it in the web app).
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "scripts" / "runner-agent" / "template.md"
AGENTS = ROOT / "agents"

BASE_TOOLS = "Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Skill"
APPIUM = "mcp__plugin_exploratory-testing_appium-mcp"
XCODE = "mcp__plugin_exploratory-testing_xcodebuild"
PLAYWRIGHT = "mcp__plugin_exploratory-testing_playwright"

WRONG_RUNNER = (
    "- **Right Runner check.** The `Target:` line in the charter's Setup row must be `{target}`. If it names another kind of target, "
    "you were given the wrong Runner and lack the tools: write `wrong runner type: the charter needs <its Target>` as the first line of "
    '"Problems", change nothing else and reply with "STATUS: session-done" and your TOOL_CALLS_USED.'
)

MOBILE_OUTPUT = (
    "`appium_get_page_source` returns a compact list of the visible elements and the path of the full XML file. Grep that file for "
    "anything the list does not show; do not call the tool again to see the same screen. `appium_screenshot` returns the path of a "
    "PNG file and a small preview image; Read the PNG only for a pixel-exact check."
)
WEB_OUTPUT = (
    "Use `browser_snapshot` (text) to read a page and `browser_take_screenshot` only when the look is the evidence. Ask for the "
    "console and network output filtered (errors only, a URL pattern) where the tool allows it."
)

VARIANTS = {
    "mobile": {
        "description": (
            "Executes ONE LEG of one exploratory test session on a mobile app target (iOS or Android, through Appium and XcodeBuildMCP) "
            "for a charter handed over by the exploratory-testing orchestrator skill, and writes SBTM notes to disk. "
            "Use only when that skill delegates a charter whose Target is mobile."
        ),
        "tools": f"{BASE_TOOLS}, {APPIUM}, {XCODE}",
        "secret_tools": "`appium_set_value`",
        "output_rules": MOBILE_OUTPUT,
        "target_section": (
            "\n## Your toolset: mobile\n"
            "You drive a mobile app with the Appium tools (and XcodeBuildMCP for building, installing and launching an iOS build). "
            "Prefer the accessibility id or id as a locator, and xpath only when nothing else works.\n"
            + WRONG_RUNNER.format(target="mobile")
        ),
    },
    "web": {
        "description": (
            "Executes ONE LEG of one exploratory test session on a web (or API) target, through Playwright, "
            "for a charter handed over by the exploratory-testing orchestrator skill, and writes SBTM notes to disk. "
            "Use only when that skill delegates a charter whose Target is web."
        ),
        "tools": f"{BASE_TOOLS}, {PLAYWRIGHT}",
        "secret_tools": "`browser_type`, `browser_fill_form`",
        "output_rules": WEB_OUTPUT,
        "target_section": (
            "\n## Your toolset: web\n"
            "You drive a web application with the Playwright tools; API checks go through Bash (curl) as the Rules of engagement allow.\n"
            + WRONG_RUNNER.format(target="web")
        ),
    },
    "mobile-web": {
        "description": (
            "Executes ONE LEG of one exploratory test session that uses BOTH a mobile app and a web app (for example, a request created "
            "in the mobile app and approved in the web app), through Appium, XcodeBuildMCP and Playwright, for a charter handed over by the "
            "exploratory-testing orchestrator skill, and writes SBTM notes to disk. Use only when that skill delegates a charter whose Target is mobile-web."
        ),
        "tools": f"{BASE_TOOLS}, {APPIUM}, {XCODE}, {PLAYWRIGHT}",
        "secret_tools": "`appium_set_value`, `browser_type`, `browser_fill_form`",
        "output_rules": MOBILE_OUTPUT + " " + WEB_OUTPUT,
        "target_section": (
            "\n## Your toolset: mobile and web\n"
            "You have both the mobile tools (Appium, XcodeBuildMCP) and the web tools (Playwright). A scenario may start in one client and "
            "continue in the other. Log in to each client with the account role the charter names for it. In every Test Notes line say which "
            "client and role the step ran in. Keep the identifiers of data you carry from one client to the other (a request id, a name) in "
            '"Current state of the app" in the Handoff file.\n'
            + WRONG_RUNNER.format(target="mobile-web")
        ),
    },
}


def render(name: str) -> str:
    v = VARIANTS[name]
    text = TEMPLATE.read_text(encoding="utf-8")
    for key, value in {
        "{{NAME}}": f"session-runner-{name}",
        "{{DESCRIPTION}}": v["description"],
        "{{TOOLS}}": v["tools"],
        "{{SECRET_TOOLS}}": v["secret_tools"],
        "{{OUTPUT_RULES}}": v["output_rules"],
        "{{TARGET_SECTION}}": v["target_section"],
    }.items():
        text = text.replace(key, value)
    assert "{{" not in text, "unreplaced placeholder"
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if a file is out of date")
    args = parser.parse_args()
    stale = []
    for name in VARIANTS:
        path = AGENTS / f"session-runner-{name}.md"
        text = render(name)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("out of date (run scripts/build_runner_agents.py): " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
