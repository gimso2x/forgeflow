#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class RequiredModule:
    import_name: str
    package_name: str


DEFAULT_MODULES = [
    RequiredModule("jsonschema", "jsonschema"),
    RequiredModule("yaml", "PyYAML"),
    RequiredModule("pytest", "pytest"),
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check first-clone Python dependencies for ForgeFlow.",
    )
    parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="Extra import module to check; useful for smoke-testing error output.",
    )
    return parser.parse_args()


def _missing_modules(modules: list[RequiredModule]) -> list[RequiredModule]:
    return [module for module in modules if importlib.util.find_spec(module.import_name) is None]


def main() -> int:
    args = _parse_args()
    modules = [*DEFAULT_MODULES, *(RequiredModule(name, name) for name in args.module)]
    missing = _missing_modules(modules)

    if missing:
        print("ENVIRONMENT CHECK: FAIL")
        for module in missing:
            print(f"Missing Python module: {module.import_name} (package: {module.package_name})")
        print("Run: make setup")
        print("Then retry: make check-env && make validate")
        return 1

    print("ENVIRONMENT CHECK: PASS")
    print("Python dependencies available: " + ", ".join(module.package_name for module in modules))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
