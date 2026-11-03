#!/usr/bin/env python3
"""One-command preflight: is the exploratory testing setup usable right now?

Usage:
    check_setup.py --config <config.yaml> [--env NAME | --all-envs]
                   [--targets web,api,ios,android] [--offline]
                   [--project-root DIR] [--secrets-file FILE]

What it does, in order:
  1. config file exists and passes validate_config.py
  2. the chosen environment(s) exist (with several environments you must say which)
  3. every secret the environment needs is set (check_secret.py)
  4. things that look like a setup mistake (environment name versus safety level, a
     "no login needed" site that redirects to a login page)
  5. targets are reachable: web and API URLs, build tools, simulators/emulators/devices

Each line starts with one of:
  PASS  the check ran and is fine
  FAIL  the run cannot work until this is fixed
  WARN  probably fine, but worth a look; never stops the run
  SKIP  not applicable, switched off (--offline, --targets), or blocked by an earlier FAIL

"Reachable" means any HTTP response, including 401, 403, 404 or 5xx. Only DNS,
connection, TLS and timeout errors fail. Requests carry no credentials.
Jira/Confluence cannot be checked here (they are reached through connectors).

Output never contains secret values or URL credentials.

Exit codes: 0 = no FAIL (warnings allowed), 1 = at least one FAIL,
            2 = could not run, 3 = environment choice needed (names are listed).
"""
import argparse
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:
    print("Missing dependency 'pyyaml'. Run: pip install pyyaml jsonschema", file=sys.stderr)
    sys.exit(2)

SCRIPTS = Path(__file__).resolve().parent
TIMEOUT = 10          # seconds per HTTP request
TOOL_TIMEOUT = 30     # seconds per helper command (xcrun, adb ...)
LOGIN_WORDS = re.compile(r"log-?in|sign-?in|sso|oauth|/auth", re.I)
PROD_WORDS = {"prod", "production", "live"}
NONPROD_WORDS = {"test", "dev", "qa", "staging", "stage", "uat", "sandbox"}


class Report:
    def __init__(self):
        self.items = []

    def add(self, status, area, detail):
        self.items.append((status, area, detail))
        print(f"{status:<4}  {area}: {detail}")

    def count(self, status):
        return sum(1 for s, _, _ in self.items if s == status)


# --------------------------------------------------------------------------- helpers

def safe_url(url):
    """URL without credentials or query string, for printing."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host += f":{parts.port}"
    return f"{parts.scheme}://{host}{parts.path}"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url):
    """Return (status, location, None) for any HTTP answer, or (None, None, reason) on failure."""
    parts = urlsplit(url)  # urllib cannot connect to user:pw@host, and requests carry no credentials anyway
    host = parts.hostname + (f":{parts.port}" if parts.port else "") if parts.hostname else ""
    url = parts._replace(netloc=host).geturl()
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "exploratory-testing-preflight"})
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            return response.status, response.headers.get("Location"), None
    except urllib.error.HTTPError as exc:            # any HTTP answer, 3xx to 5xx, counts as reachable
        return exc.code, exc.headers.get("Location"), None
    except urllib.error.URLError as exc:
        return None, None, classify(exc.reason)
    except Exception as exc:                          # noqa: BLE001 (timeouts raised while reading, etc.)
        return None, None, classify(exc)


def classify(reason):
    if isinstance(reason, socket.gaierror):
        return "DNS lookup failed"
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason):
        return f"timed out after {TIMEOUT}s"
    if isinstance(reason, ssl.SSLError):
        return "TLS error"
    return "connection failed"


def run(cmd, cwd=None):
    """Run a helper command; return (exit_code, stdout) or (None, '') if it cannot run."""
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=TOOL_TIMEOUT, cwd=cwd)
        return done.returncode, done.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None, ""


def is_macos():
    return sys.platform == "darwin"


# --------------------------------------------------------------------------- checks

def check_config(config, root, report):
    """Run the validator. Return (cfg, validator_warnings) or (None, None) if the config is unusable."""
    if not config.exists():
        report.add("FAIL", "config", f"{config} does not exist; run /exploratory-testing:setup")
        return None, None
    code, out = run([sys.executable, str(SCRIPTS / "validate_config.py"), str(config),
                     "--project-root", str(root)])
    if code is None or code == 2:
        print("Could not run validate_config.py (is 'pip install pyyaml jsonschema' done?)", file=sys.stderr)
        sys.exit(2)
    warns = []
    for line in out.splitlines():
        if line.startswith("WARN "):
            warns.append(line[5:])
    if code != 0:
        errors = [line[6:] for line in out.splitlines() if line.startswith("ERROR ")]
        for line in errors[:10]:
            report.add("FAIL", "config", line)
        if len(errors) > 10:
            report.add("FAIL", "config", f"... and {len(errors) - 10} more; run validate_config.py")
        report.add("FAIL", "config", "invalid; run /exploratory-testing:setup to fix it")
        return None, None
    report.add("PASS", "config", f"valid ({len(warns)} warning(s) from the validator)" if warns else "valid")
    return yaml.safe_load(config.read_text(encoding="utf-8")), warns


def check_secrets(config, env_name, secrets_file, report):
    cmd = [sys.executable, str(SCRIPTS / "check_secret.py"), "check", str(config), "--env", env_name]
    if secrets_file:
        cmd += ["--secrets-file", str(secrets_file)]
    code, out = run(cmd)
    if code is None or code == 2:
        report.add("FAIL", "secrets", "could not check the secrets file")
        return
    for line in out.splitlines():
        if line.startswith("WARN "):
            report.add("WARN", "secrets", line[5:])
    if code == 0:
        total = re.search(r"All (\d+) secret", out)
        report.add("PASS", "secrets", f"all {total.group(1)} set" if total else "none needed")
        return
    missing = [line.split()[1] for line in out.splitlines() if line.startswith("missing ")]
    report.add("FAIL", "secrets", f"{len(missing)} not set: {', '.join(missing)}")
    report.add("FAIL", "secrets", f'to fix: run check_secret.py template "{config}" --env {env_name}, '
                                  f"edit the secrets file, run again")


def check_safety_hints(env, report):
    tokens = set(re.split(r"[-_]", env["name"].lower()))
    kind = env["safety"]["kind"]
    if tokens & PROD_WORDS and kind != "production":
        report.add("WARN", "safety", f"name '{env['name']}' sounds like production but safety.kind is '{kind}'")
    if kind == "production" and tokens & NONPROD_WORDS:
        report.add("WARN", "safety", f"name '{env['name']}' sounds like a test environment but "
                                     f"safety.kind is 'production' (stricter than needed)")


def check_url(area, url, report, offline, not_needed=False):
    if offline:
        report.add("SKIP", area, f"{safe_url(url)} (--offline)")
        return
    status, location, problem = fetch(url)
    if problem:
        report.add("FAIL", area, f"{safe_url(url)} not reachable: {problem}")
        return
    report.add("PASS", area, f"{safe_url(url)} reachable (HTTP {status})")
    if not_needed and status in (301, 302, 303, 307, 308) and location and LOGIN_WORDS.search(location):
        report.add("WARN", area, "redirects to a login page, but accounts is 'not_needed'; "
                                 "add an account or allow account creation if tests need to log in")


def check_build(target, root, report):
    area = f"{target['type']} build"
    build = target.get("build")
    if not build:
        return
    kind = build["type"]
    if kind == "file":
        path = root / build["path"]
        report.add("PASS" if path.exists() else "FAIL", area, f"prebuilt file {build['path']}"
                   + ("" if path.exists() else " not found"))
        return
    if kind == "distribution":
        report.add("PASS", area, f"uses the {build['channel']} build; nothing to build")
        return
    tool = build["tool"]
    if "project_path" in build and not (root / build["project_path"]).exists():
        report.add("WARN", area, f"project_path {build['project_path']} not found")
    if tool == "xcodebuild":
        found = is_macos() and shutil.which("xcodebuild")
        report.add("PASS" if found else "FAIL", area,
                   "xcodebuild found" if found else "xcodebuild not found (needs macOS with Xcode)")
    elif tool == "gradle":
        base = root / build.get("project_path", "")
        wrapper = (base / "gradlew").exists() or (root / "gradlew").exists()
        found = wrapper or shutil.which("gradle")
        report.add("PASS" if found else "FAIL", area,
                   "gradle found" if found else "neither gradlew nor gradle found")
    elif tool == "flutter":
        found = shutil.which("flutter")
        report.add("PASS" if found else "FAIL", area, "flutter found" if found else "flutter not found")
    elif tool in ("react_native", "expo"):
        found = shutil.which("npx") or shutil.which("node")
        report.add("PASS" if found else "FAIL", area, "node/npx found" if found else "node/npx not found")
    else:  # other: first word of the command
        try:
            first = shlex.split(build["command"])[0]
        except (ValueError, IndexError):
            report.add("FAIL", area, "command is empty or malformed")
            return
        found = shutil.which(first) or (root / first).exists()
        report.add("PASS" if found else "FAIL", area, f"'{first}' found" if found else f"'{first}' not found")


def check_ios_devices(report):
    if not is_macos() or not shutil.which("xcrun"):
        report.add("FAIL", "ios devices", "needs macOS with Xcode command line tools (xcrun not found)")
        return
    code, out = run(["xcrun", "simctl", "list", "devices", "available"])
    if code is None or code != 0:
        report.add("FAIL", "ios devices", "could not list simulators")
        return
    sims = [line for line in out.splitlines() if re.search(r"\([0-9A-Fa-f-]{36}\)", line)]
    booted = [line for line in sims if "(Booted)" in line]
    if booted:
        report.add("PASS", "ios devices", f"{len(sims)} simulator(s), {len(booted)} running")
    elif sims:
        report.add("PASS", "ios devices", f"{len(sims)} simulator(s), none running (the run can start one)")
    else:
        report.add("FAIL", "ios devices", "no simulator available")


def check_android_devices(report):
    if not shutil.which("adb"):
        report.add("FAIL", "android devices", "adb not found (install Android platform-tools)")
        return
    code, out = run(["adb", "devices"])
    if code is None or code != 0:
        report.add("FAIL", "android devices", "could not run adb devices")
        return
    online = [line for line in out.splitlines()[1:] if line.strip().endswith("device")]
    if online:
        report.add("PASS", "android devices", f"{len(online)} device or emulator connected")
        return
    avds = []
    if shutil.which("emulator"):
        code, out = run(["emulator", "-list-avds"])
        avds = [line for line in out.splitlines() if line.strip()] if code == 0 else []
    if avds:
        report.add("PASS", "android devices", f"{len(avds)} emulator(s) defined, none running (the run can start one)")
    else:
        report.add("FAIL", "android devices", "no device connected and no emulator defined")


def check_environment(env, idx, validator_warns, args, root, report):
    print(f"\nEnvironment '{env['name']}' (safety: {env['safety']['kind']})")
    for warn in validator_warns:
        if warn.startswith(f"environments[{idx}]") and ".build." not in warn:
            report.add("WARN", "config", warn)

    if args.secrets_blocked:
        report.add("SKIP", "secrets", "blocked by earlier failure")
    else:
        check_secrets(args.config, env["name"], args.secrets_file, report)

    check_safety_hints(env, report)

    wanted = args.targets
    not_needed = env["accounts"] == "not_needed"
    need_ios = need_android = False
    for target in env["targets"]:
        kind = target["type"]
        if wanted and kind not in wanted:
            report.add("SKIP", kind, "not requested (--targets)")
            continue
        if kind == "web":
            check_url("web", target["url"], report, args.offline, not_needed)
        elif kind == "api":
            check_url("api", target["base_url"], report, args.offline)
            spec = target.get("spec")
            if spec and spec.startswith("https://"):
                check_url("api spec", spec, report, args.offline)
        else:
            check_build(target, root, report)
            need_ios |= kind == "ios"
            need_android |= kind == "android"
    if need_ios:
        check_ios_devices(report)
    if need_android:
        check_android_devices(report)


# --------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Preflight check for the exploratory testing setup")
    ap.add_argument("--config", type=Path, required=True)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--env", help="environment to check")
    group.add_argument("--all-envs", action="store_true")
    ap.add_argument("--targets", help="comma-separated subset of: web,api,ios,android")
    ap.add_argument("--offline", action="store_true", help="skip every network check")
    ap.add_argument("--project-root", type=Path, help="default: the folder above the config's folder")
    ap.add_argument("--secrets-file", type=Path)
    args = ap.parse_args(argv)

    args.targets = {t.strip() for t in args.targets.split(",") if t.strip()} if args.targets else set()
    unknown = args.targets - {"web", "api", "ios", "android"}
    if unknown:
        print(f"Unknown target type(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2
    root = (args.project_root or args.config.resolve().parent.parent).resolve()
    args.secrets_blocked = False

    report = Report()
    cfg, validator_warns = check_config(args.config, root, report)
    if cfg is None:
        for area in ("environment", "secrets", "targets"):
            report.add("SKIP", area, "blocked by invalid or missing config")
        summarize(report)
        return 1

    envs = cfg["environments"]
    names = [e["name"] for e in envs]
    if args.all_envs:
        chosen = list(enumerate(envs))
    elif args.env:
        if args.env not in names:
            print(f"\nNo environment named '{args.env}'. Choose one of: {', '.join(names)}")
            return 3
        chosen = [(names.index(args.env), envs[names.index(args.env)])]
    elif len(envs) == 1:
        chosen = [(0, envs[0])]
    else:
        print(f"\nSeveral environments: {', '.join(names)}. Ask the user which one, then run again with --env NAME.")
        return 3

    for idx, env in chosen:
        check_environment(env, idx, validator_warns, args, root, report)
    summarize(report)
    return 1 if report.count("FAIL") else 0


def summarize(report):
    print(f"\nResult: {report.count('PASS')} PASS, {report.count('FAIL')} FAIL, "
          f"{report.count('WARN')} WARN, {report.count('SKIP')} SKIP")


if __name__ == "__main__":
    sys.exit(main())
