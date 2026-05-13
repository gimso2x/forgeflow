"""Template for future ForgeFlow artifact schema migrations.

Do not import this file from runtime. Runtime migration code lives in
`forgeflow_runtime/artifact_migrations.py`; this file is a copy/paste scaffold
for the next real version bump.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SOURCE_VERSION = "0.2"
TARGET_VERSION = "0.2"
STEP_NAME = "0.2 -> 0.2 no-op"


def transform(payload: dict[str, Any], *, source_version: str = SOURCE_VERSION, target_version: str = TARGET_VERSION) -> dict[str, Any]:
    """Return a migrated copy of an artifact payload.

    Replace this no-op with explicit field transforms when a real target schema
    appears. Keep the function pure: never mutate `payload` in place and never
    perform filesystem I/O here.
    """
    if source_version != SOURCE_VERSION or target_version != TARGET_VERSION:
        raise ValueError(f"unsupported migration {source_version} -> {target_version}")
    migrated = deepcopy(payload)
    migrated["schema_version"] = target_version
    return migrated
