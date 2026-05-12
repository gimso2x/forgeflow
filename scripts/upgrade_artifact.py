#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from forgeflow_runtime.artifact_migrations import CURRENT_ARTIFACT_SCHEMA_VERSION, migrate_artifact_payload
from forgeflow_runtime.artifact_validation import validate_artifact_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upgrade a ForgeFlow JSON artifact to the current supported schema version."
    )
    parser.add_argument("--artifact-name", required=True, help="Artifact contract name, e.g. brief, plan, run-state")
    parser.add_argument("--path", required=True, type=Path, help="Path to a .forgeflow/tasks/* artifact JSON file")
    parser.add_argument("--target-version", default=CURRENT_ARTIFACT_SCHEMA_VERSION)
    parser.add_argument("--check", action="store_true", help="Validate and report migration without writing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    migrated, report = migrate_artifact_payload(
        artifact_name=args.artifact_name,
        payload=payload,
        source_name=args.path.name,
        target_version=args.target_version,
    )
    validate_artifact_payload(artifact_name=args.artifact_name, payload=migrated, source_name=args.path.name)
    if not args.check:
        args.path.write_text(json.dumps(migrated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    action = "checked" if args.check else "upgraded"
    print(
        f"{action} {args.path}: {report.artifact_name} {report.from_version}->{report.to_version} "
        f"changed={str(report.changed).lower()} steps={', '.join(report.steps)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
