#!/usr/bin/env python3
"""Check which secrets the config needs and whether each one is set.

Secrets are referenced in config.yaml as 'secret:NAME' and kept in one file
that you edit yourself:

    ~/.exploratory-testing/secrets.env        (override with --secrets-file)

Format: one NAME=value per line. Everything after the first '=' is the value,
verbatim, so do NOT wrap it in quotes. Blank lines and lines starting with '#'
are ignored. An empty value (NAME=) counts as not set.

Commands:
    check    CONFIG   List the secrets the config needs and whether each is set.
    template CONFIG   Add empty NAME= lines for secrets that have no entry yet,
                      so you only have to type the values.

Neither command ever prints a secret value, and neither asks for input.

Exit codes: 0 = all secrets set, 1 = some missing, 2 = could not run.
"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Missing dependency 'pyyaml'. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

DEFAULT_SECRETS_FILE = Path.home() / ".exploratory-testing" / "secrets.env"
NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")
REF_RE = re.compile(r"^secret:([A-Z_][A-Z0-9_]*)$")
HEADER = ("# Secrets for the exploratory testing plugin. One NAME=value per line.\n"
          "# Type each value right after the '=' sign: no quotes. Keep this file private.\n\n")


# --------------------------------------------------------------------------- secrets file

def parse_secrets(path):
    """Return ({NAME: value}, [warnings]). Values are verbatim; warnings never contain a value."""
    values, counts, warnings = {}, {}, []
    if not path.exists():
        return values, warnings
    # utf-8-sig: tolerate the byte-order mark some Windows editors add
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        name, sep, value = raw.partition("=")
        name = name.strip()
        if not sep or not NAME_RE.match(name):
            warnings.append(f"line {number} is not NAME=value (NAME in capitals, digits, underscores); ignored")
            continue
        counts[name] = counts.get(name, 0) + 1
        values[name] = value
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            warnings.append(f"{name}: value is wrapped in quotes, and the quotes count as part of the value; "
                            f"remove them unless they belong to the secret")
        elif value != value.strip():
            warnings.append(f"{name}: value has leading or trailing spaces")
    warnings += [f"{name}: appears {n} times; the last one is used" for name, n in counts.items() if n > 1]
    return values, warnings


def add_empty_entries(path, names):
    """Append NAME= lines, leaving everything already in the file untouched."""
    text = path.read_text(encoding="utf-8-sig") if path.exists() else HEADER
    if text and not text.endswith("\n"):
        text += "\n"
    text += "".join(f"{name}=\n" for name in names)

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".secrets-")  # created with mode 0600
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def permission_warning(path):
    if os.name != "posix" or not path.exists():
        return None
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        return f'{path} can be read by other users (mode {mode:03o}); run: chmod 600 "{path}"'
    return None


# --------------------------------------------------------------------------- config

def label_for(cfg, path):
    """Describe where a reference sits, without any secret: environment, account or target."""
    try:
        if path[0] == "environments":
            env = cfg["environments"][path[1]]
            label = f"environment '{env['name']}'"
            if path[2] == "accounts":
                return f"{label}, account {env['accounts'][path[3]]['username']}"
            if path[2] == "targets":
                return f"{label}, {env['targets'][path[3]]['type']} target"
            return label
    except (KeyError, IndexError, TypeError):
        pass
    return ".".join(str(p) for p in path)


def collect_refs(cfg):
    """Return {NAME: [labels]} for every '*_ref: secret:NAME' in the config, in file order."""
    refs = {}

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, path + [key])
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, path + [index])
        elif isinstance(node, str) and path and str(path[-1]).endswith("_ref"):
            match = REF_RE.match(node)
            if match:
                refs.setdefault(match.group(1), []).append(label_for(cfg, path))

    walk(cfg, [])
    return refs


def load_refs(config_path):
    """Parse the config and return its references, or None after printing why not."""
    try:
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"Cannot read config {config_path}: {exc.strerror}", file=sys.stderr)
        return None
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"line {mark.line + 1}" if mark else "file"
        print(f"Cannot parse config {config_path} ({where}); run the config validator first", file=sys.stderr)
        return None
    if not isinstance(cfg, dict):
        print(f"Cannot use config {config_path}: expected a mapping of settings", file=sys.stderr)
        return None
    return collect_refs(cfg)


# --------------------------------------------------------------------------- commands

def cmd_check(args):
    refs = load_refs(args.config)
    if refs is None:
        return 2
    if not refs:
        print("No secrets are referenced in this config.")
        return 0

    values, warnings = parse_secrets(args.secrets_file)
    print(f"Secrets file: {args.secrets_file}" + ("" if args.secrets_file.exists() else " (not created yet)"))
    width = max(len(name) for name in refs)
    missing = [name for name in refs if not values.get(name)]
    for name, labels in refs.items():
        where = labels[0] + (f" (+{len(labels) - 1} more)" if len(labels) > 1 else "")
        print(f"{'missing' if name in missing else 'found  '}  {name.ljust(width)}  {where}")
    print(f"{len(missing)} of {len(refs)} secret(s) missing" if missing else f"All {len(refs)} secret(s) are set")

    warnings.append(permission_warning(args.secrets_file))
    for warning in filter(None, warnings):
        print(f"WARN {warning}")

    if missing:
        steps = []
        if any(name not in values for name in missing):
            steps.append(f'Run: python "{Path(__file__).resolve()}" template "{args.config.resolve()}"'
                         f"   (adds the empty NAME= lines)")
        steps.append(f"Open {args.secrets_file} in an editor and type each value right after its '=' sign "
                     f"(no quotes).")
        steps.append("Run check again.")
        print("\nTo fix:")
        for number, step in enumerate(steps, start=1):
            print(f"  {number}. {step}")
    return 1 if missing else 0


def cmd_template(args):
    refs = load_refs(args.config)
    if refs is None:
        return 2
    values, _ = parse_secrets(args.secrets_file)
    new = [name for name in refs if name not in values]
    if new:
        add_empty_entries(args.secrets_file, new)
        print(f"Added {len(new)} empty entr{'y' if len(new) == 1 else 'ies'} to {args.secrets_file}:")
        for name in new:
            print(f"  {name}=")
    else:
        print(f"Every referenced secret already has an entry in {args.secrets_file}.")
    if any(not values.get(name) for name in refs):  # includes the entries just added
        print("Open the file, type each value right after the '=' sign (no quotes), save, then run check.")
    return 0


# --------------------------------------------------------------------------- main

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--secrets-file", type=Path, default=DEFAULT_SECRETS_FILE,
                        help=f"default: {DEFAULT_SECRETS_FILE}")
    parser = argparse.ArgumentParser(description="Check the plugin's secrets file against a config.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func, text in (
            ("check", cmd_check, "show which secrets the config needs and whether each is set"),
            ("template", cmd_template, "add empty NAME= lines for secrets that have no entry")):
        p = sub.add_parser(name, parents=[common], help=text)
        p.add_argument("config", type=Path)
        p.set_defaults(func=func)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except OSError as exc:
        print(f"Cannot use secrets file {args.secrets_file}: {exc.strerror}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
