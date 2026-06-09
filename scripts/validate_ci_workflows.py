#!/usr/bin/env python3
"""Validate CI workflow files reference correct make targets and declare minimal permissions."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(".")


def _contains(path: pathlib.Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    validate_wf = ROOT / ".github" / "workflows" / "validate.yml"
    evals_wf = ROOT / ".github" / "workflows" / "evals.yml"
    readme = ROOT / "README.md"
    evals_readme = ROOT / "evals" / "README.md"

    def check(path: pathlib.Path, needle: str, error: str) -> None:
        if not _contains(path, needle):
            failures.append(error)

    check(validate_wf, "run: make validate",
           "ERROR: validate workflow must run make validate")
    check(evals_wf, "run: make validate-evals",
           "ERROR: evals workflow must run the documented eval fixture bundle")
    check(validate_wf, "permissions:",
           "ERROR: validate workflow must declare minimal permissions")
    check(evals_wf, "permissions:",
           "ERROR: evals workflow must declare minimal permissions")
    check(validate_wf, "contents: read",
           "ERROR: validate workflow must use read-only contents permission")
    check(evals_wf, "contents: read",
           "ERROR: evals workflow must use read-only contents permission")
    check(readme, ".github/workflows/validate.yml",
           "ERROR: README must document validate workflow location")
    check(readme, ".github/workflows/evals.yml",
           "ERROR: README must document evals workflow location")
    check(readme, "read-only `contents: read` permissions",
           "ERROR: README must document CI workflows use minimal read-only permissions")
    check(readme, "make validate-evals",
           "ERROR: README must document the eval validation bundle target")
    check(evals_readme, "make validate-evals",
           "ERROR: eval README must document the eval validation bundle target")

    if failures:
        for f in failures:
            print(f)
        return 1

    print("OK: CI workflows invoke documented local validation bundles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
