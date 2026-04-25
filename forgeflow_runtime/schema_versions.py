from __future__ import annotations

from typing import Any

from forgeflow_runtime.errors import RuntimeViolation

CURRENT_ARTIFACT_SCHEMA_VERSION = "0.1"


def assert_supported_artifact_schema_version(*, payload: dict[str, Any], source_name: str) -> None:
    schema_version = payload.get("schema_version")
    if schema_version != CURRENT_ARTIFACT_SCHEMA_VERSION:
        raise RuntimeViolation(
            f"{source_name} uses unsupported schema_version {schema_version}; "
            f"supported artifact schema_version is {CURRENT_ARTIFACT_SCHEMA_VERSION}"
        )
