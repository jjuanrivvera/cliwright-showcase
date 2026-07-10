#!/usr/bin/env python3
"""Validate every registry entry against the schema and compile them into
site/registry.json, which the static site renders client-side.

Run locally:  python3 scripts/build.py
CI runs the same script: a bad PR fails here before it can merge or deploy.
"""
from __future__ import annotations

import json
import pathlib
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry"
SCHEMA = ROOT / "schema" / "entry.schema.json"
OUT = ROOT / "site" / "registry.json"


def fail(msg: str) -> None:
    print(f"✗ {msg}", file=sys.stderr)


def main() -> int:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text()))
    entries: list[dict] = []
    errors = 0
    names: dict[str, str] = {}

    for path in sorted(REGISTRY.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            fail(f"{path.name}: invalid YAML: {e}")
            errors += 1
            continue
        if not isinstance(data, dict):
            fail(f"{path.name}: must be a single YAML mapping")
            errors += 1
            continue

        schema_errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        for e in schema_errors:
            loc = "/".join(str(p) for p in e.path) or "(root)"
            fail(f"{path.name}: {loc}: {e.message}")
        errors += len(schema_errors)
        if schema_errors:
            continue

        # Filename must equal the entry name, so the registry has one file per tool
        # and PRs never collide silently.
        if data["name"] != path.stem:
            fail(f"{path.name}: name '{data['name']}' must match filename '{path.stem}'")
            errors += 1
            continue
        if data["name"] in names:
            fail(f"{path.name}: duplicate name '{data['name']}' (also in {names[data['name']]})")
            errors += 1
            continue
        names[data["name"]] = path.name
        data.setdefault("agent_ready", True)
        entries.append(data)

    if errors:
        fail(f"{errors} validation error(s) — fix the entries above.")
        return 1

    entries.sort(key=lambda d: d["name"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"count": len(entries), "tools": entries}, indent=2) + "\n")
    print(f"✓ {len(entries)} entries valid → {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
