#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
import venv
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
    parser.add_argument(
        "--skip-modules",
        action="store_true",
        help="Only skip Python module checks; useful before make setup installs dependencies.",
    )
    parser.add_argument(
        "--require-venv-support",
        action="store_true",
        help="Fail if venv/ensurepip is unavailable; used by setup preflight only.",
    )
    return parser.parse_args()


def _missing_modules(modules: list[RequiredModule]) -> list[RequiredModule]:
    return [module for module in modules if importlib.util.find_spec(module.import_name) is None]


def _venv_available() -> bool:
    return getattr(venv, "EnvBuilder", None) is not None and importlib.util.find_spec("ensurepip") is not None


def main() -> int:
    args = _parse_args()
    if args.require_venv_support and not _venv_available():
        print("ENVIRONMENT CHECK: FAIL")
        print("Python venv/ensurepip support is unavailable.")
        print("On Ubuntu/Debian, run: sudo apt-get install python3-venv")
        print("Then retry: make setup")
        return 1

    modules = [*DEFAULT_MODULES, *(RequiredModule(name, name) for name in args.module)]
    missing = [] if args.skip_modules else _missing_modules(modules)

    if missing:
        print("ENVIRONMENT CHECK: FAIL")
        for module in missing:
            print(f"Missing Python module: {module.import_name} (package: {module.package_name})")
        print("Run: make setup")
        print("Then retry: make check-env && make validate")
        return 1

    print("ENVIRONMENT CHECK: PASS")
    if args.skip_modules:
        print("Python module checks skipped")
    else:
        print("Python dependencies available: " + ", ".join(module.package_name for module in modules))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
