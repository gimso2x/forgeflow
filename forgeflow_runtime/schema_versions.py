from __future__ import annotations

from typing import Any

from forgeflow_runtime.artifact_migrations import (
    CURRENT_ARTIFACT_SCHEMA_VERSION,
    assert_supported_artifact_schema_version,
)

__all__ = ["CURRENT_ARTIFACT_SCHEMA_VERSION", "assert_supported_artifact_schema_version"]
