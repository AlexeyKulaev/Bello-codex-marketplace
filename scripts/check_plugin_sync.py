#!/usr/bin/env python3
"""Read-only check that the shared plugin and its tests match a pinned Bello commit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TESTS = {
    "tests/test_config_advisor.py": "tests/test_config_advisor_060.py",
    "tests/test_plugin_packaging.py": "tests/test_plugin_packaging.py",
}


def source_metadata() -> dict:
    metadata = json.loads((ROOT / "bello-source.json").read_text(encoding="utf-8"))
    if (metadata.get("repository") != "Makson179/Bello"
            or metadata.get("plugin") != "plugins/bello"
            or metadata.get("tests") != TESTS
            or not re.fullmatch(r"[0-9a-f]{40}", str(metadata.get("commit", "")))):
        raise ValueError("bello-source.json must pin the expected repository, plugin, tests and full commit")
    return metadata


def git(source: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(source), *args])


def check(source: Path, metadata: dict) -> None:
    commit = metadata["commit"]
    if git(source, "rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("Source checkout is not the pinned Bello commit")
    expected = {}
    tree = git(source, "ls-tree", "-r", "-z", commit, "--", "plugins/bello")
    for record in tree.split(b"\0"):
        if not record:
            continue
        info, raw_path = record.split(b"\t", 1)
        mode, kind, _ = info.split()
        path = raw_path.decode("utf-8")
        if (kind != b"blob" or mode not in (b"100644", b"100755")
                or not path.startswith("plugins/bello/")
                or ".." in Path(path).parts):
            raise ValueError(f"Unsupported source entry: {path}")
        expected[path] = git(source, "show", f"{commit}:{path}")
    if not expected:
        raise ValueError("Pinned commit contains no plugin")
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "plugins/bello").rglob("*")
        if (path.is_file() or path.is_symlink())
        and "__pycache__" not in path.parts and path.suffix not in (".pyc", ".pyo")
    }
    if actual != set(expected):
        raise ValueError(f"Plugin file set differs: {sorted(actual ^ set(expected))}")
    expected.update({target: git(source, "show", f"{commit}:{origin}") for target, origin in TESTS.items()})
    for relative, content in expected.items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ValueError(f"Out-of-sync file: {relative}")
    print(f"Plugin and {len(TESTS)} test files match Bello {commit}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Local checkout of the pinned Bello commit")
    parser.add_argument("--print-source", action="store_true", help="Print validated commit for CI checkout")
    args = parser.parse_args()
    metadata = source_metadata()
    if args.print_source:
        print(f"commit={metadata['commit']}")
    elif args.source is not None:
        check(args.source, metadata)
    else:
        parser.error("pass --source or --print-source")


if __name__ == "__main__":
    main()
