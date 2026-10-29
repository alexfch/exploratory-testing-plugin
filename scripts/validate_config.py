#!/usr/bin/env python3
"""Validate a plugin config.yaml.

Usage:
    validate.py <config.yaml> [--project-root DIR] [--schema FILE]

Checks, in order:
  1. The file parses as YAML, with no duplicate keys.
  2. schema_version is one this plugin understands.
  3. The config matches schemas/config.schema.json.
  4. Rules the schema cannot express (unique names, tool/platform match,
     paths that exist).

Output is short on purpose: one line per problem, never the offending value
(a mistyped *_ref could be a real secret, and this output ends up in the chat).

Exit codes: 0 = valid (warnings allowed), 1 = invalid config, 2 = could not run.
"""
import argparse
import sys
from pathlib import Path

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError as exc:
    print(f"Missing dependency '{exc.name}'. Run: pip install pyyaml jsonschema", file=sys.stderr)
    sys.exit(2)

CURRENT_VERSION = 1
# {old_version: function(cfg) -> cfg for old_version + 1}. Empty until the schema first changes.
MIGRATIONS = {}

DEFAULT_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "config.schema.json"


# --------------------------------------------------------------------------- loading

class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate keys (PyYAML silently keeps the last one)."""


def _construct_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key '{key}'", key_node.start_mark)
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


# --------------------------------------------------------------------------- messages

def fmt_path(path):
    out = ""
    for part in path:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "(root)"


def is_discriminator(err):
    """True for an error saying 'this entry's "type" is not the one this branch expects'."""
    return list(err.relative_path) == ["type"] and err.validator in ("const", "enum")


def message(err):
    """Describe an error WITHOUT echoing the offending value."""
    v, val = err.validator, err.validator_value
    last = str(err.relative_path[-1]) if err.relative_path else ""
    if v == "pattern" and last.endswith("_ref"):
        return "must be 'secret:NAME' with NAME in capitals, digits and underscores (a reference, never the secret itself)"
    if v in ("required", "additionalProperties"):
        return err.message  # names the property only
    if v == "pattern":
        return "has an invalid format"
    if v == "const":
        return f"must be {val!r}"
    if v == "enum":
        return "must be one of: " + ", ".join(map(str, val))
    if v == "type":
        return f"must be of type {val}"
    if v == "minLength":
        return "must not be empty" if val == 1 else f"must be at least {val} characters"
    if v == "maxLength":
        return f"must be at most {val} characters"
    if v == "minItems":
        return f"needs at least {val} item(s)"
    if v == "uniqueItems":
        return "items must be unique"
    return f"is invalid ({v})"


def explain(err, base=()):
    """Yield (path, message) for an error, descending into oneOf/anyOf to the branch that applies."""
    path = list(base) + list(err.relative_path)
    if err.validator in ("oneOf", "anyOf"):
        groups = {}
        for sub in err.context:
            groups.setdefault(sub.schema_path[0], []).append(sub)
        # Branches whose "type" check did not fail are the candidates for what the user meant.
        candidates = [g for g in groups.values() if not any(is_discriminator(s) for s in g)]
        if len(candidates) == 1:
            for sub in candidates[0]:
                yield from explain(sub, path)
            return
        allowed = sorted({x for g in groups.values() for s in g if is_discriminator(s)
                          for x in ([s.validator_value] if s.validator == "const" else s.validator_value)})
        if isinstance(err.instance, dict) and "type" not in err.instance:
            yield fmt_path(path), "is missing 'type'"
        elif allowed:
            yield fmt_path(path), "has an unknown 'type'; expected one of: " + ", ".join(allowed)
        else:
            yield fmt_path(path), "does not match any allowed shape"
        return
    yield fmt_path(path), message(err)


# --------------------------------------------------------------------------- semantic checks

def semantic_checks(cfg, root):
    """Rules JSON Schema cannot express. Assumes the config already passed the schema."""
    errors, warnings = [], []

    def check_path(where, rel):
        if rel and not (root / rel).exists():
            warnings.append((where, f"path '{rel}' not found under {root}"))

    seen_envs = set()
    for i, env in enumerate(cfg["environments"]):
        ep = f"environments[{i}]"
        if env["name"] in seen_envs:
            errors.append((f"{ep}.name", f"duplicate environment name '{env['name']}'"))
        seen_envs.add(env["name"])

        usernames, roles = set(), set()
        for j, acc in enumerate(env.get("accounts", [])):
            if acc["username"] in usernames:
                errors.append((f"{ep}.accounts[{j}].username", f"duplicate username '{acc['username']}' in this environment"))
            usernames.add(acc["username"])
            role = acc.get("role")
            if role and role in roles:
                warnings.append((f"{ep}.accounts[{j}].role", f"role '{role}' is used by more than one account; selecting by role is ambiguous"))
            if role:
                roles.add(role)

        for k, target in enumerate(env["targets"]):
            tp = f"{ep}.targets[{k}]"
            build = target.get("build")
            if build and build["type"] == "source":
                if build["tool"] == "xcodebuild" and target["type"] != "ios":
                    errors.append((f"{tp}.build.tool", "xcodebuild can only build an ios target"))
                if build["tool"] == "gradle" and target["type"] != "android":
                    errors.append((f"{tp}.build.tool", "gradle can only build an android target"))
                check_path(f"{tp}.build.project_path", build.get("project_path"))
            elif build and build["type"] == "file":
                check_path(f"{tp}.build.path", build["path"])
            spec = target.get("spec")
            if target["type"] == "api" and spec and not spec.startswith("https://"):
                check_path(f"{tp}.spec", spec)

    for i, source in enumerate(cfg["sources"]):
        if source["type"] == "file":
            check_path(f"sources[{i}].path", source["path"])

    return errors, warnings


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Validate a plugin config.yaml")
    ap.add_argument("config", type=Path)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--project-root", type=Path,
                    help="Base for relative paths in the config. Default: the folder above the config's folder.")
    args = ap.parse_args()

    try:
        schema = yaml.safe_load(args.schema.read_text())
    except (OSError, yaml.YAMLError) as exc:
        print(f"Cannot read schema {args.schema}: {exc}", file=sys.stderr)
        return 2
    try:
        text = args.config.read_text()
    except OSError as exc:
        print(f"Cannot read config {args.config}: {exc}", file=sys.stderr)
        return 2

    problems = lambda items, label: [f"{label} {where}: {msg}" for where, msg in items]  # noqa: E731

    # 1. Parse
    try:
        cfg = yaml.load(text, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"line {mark.line + 1}" if mark else "file"
        reason = getattr(exc, "problem", None) or "invalid YAML"
        print(f"ERROR {where}: {reason}")
        return 1
    if not isinstance(cfg, dict):
        print("ERROR (root): config must be a mapping of settings")
        return 1

    # 2. Version
    version = cfg.get("schema_version")
    if type(version) is not int:
        print("ERROR schema_version: missing or not a whole number; re-run setup")
        return 1
    if version > CURRENT_VERSION:
        print(f"ERROR schema_version: config is version {version}, but this plugin supports up to "
              f"{CURRENT_VERSION}; update the plugin")
        return 1
    while version < CURRENT_VERSION:
        if version not in MIGRATIONS:
            print(f"ERROR schema_version: config is version {version}, which this plugin can no longer "
                  f"read; re-run setup")
            return 1
        cfg = MIGRATIONS[version](cfg)
        version += 1

    # 3. Schema
    validator = Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(cfg), key=lambda e: [str(p) for p in e.path])
    lines = [(w, m) for err in schema_errors for w, m in explain(err)]
    if lines:
        print("\n".join(problems(lines, "ERROR")))
        print(f"{len(lines)} error(s)")
        return 1

    # 4. Cross-field rules
    root = args.project_root or args.config.resolve().parent.parent
    errors, warnings = semantic_checks(cfg, root.resolve())
    out = problems(errors, "ERROR") + problems(warnings, "WARN")
    if out:
        print("\n".join(out))
    if errors:
        print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
        return 1
    print(f"OK ({len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
