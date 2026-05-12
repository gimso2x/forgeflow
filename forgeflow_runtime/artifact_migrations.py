from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forgeflow_runtime.errors import RuntimeViolation

CURRENT_ARTIFACT_SCHEMA_VERSION = "0.1"
RUNTIME_VERSION_MODE = "validate_current_refuse_unknown"


@dataclass(frozen=True)
class ArtifactVersionPolicy:
    artifact_name: str
    current: str
    supported: tuple[str, ...]
    runtime_mode: str


@dataclass(frozen=True)
class ArtifactMigrationReport:
    artifact_name: str
    source_name: str
    from_version: str | None
    to_version: str
    changed: bool
    steps: list[str]


CORE_ARTIFACT_TYPES = (
    "brief",
    "plan",
    "plan-ledger",
    "decision-log",
    "run-state",
    "review-report",
    "review-report-spec",
    "review-report-quality",
    "eval-record",
    "checkpoint",
    "session-state",
    "evolution-rule",
    "experiment",
    "constraint-registry",
    "interface-spec",
    "issue-drafts",
)

ARTIFACT_VERSION_POLICY: dict[str, ArtifactVersionPolicy] = {
    artifact_name: ArtifactVersionPolicy(
        artifact_name=artifact_name,
        current=CURRENT_ARTIFACT_SCHEMA_VERSION,
        supported=(CURRENT_ARTIFACT_SCHEMA_VERSION,),
        runtime_mode=RUNTIME_VERSION_MODE,
    )
    for artifact_name in CORE_ARTIFACT_TYPES
}


def artifact_version_policy(artifact_name: str) -> ArtifactVersionPolicy:
    return ARTIFACT_VERSION_POLICY.get(
        artifact_name,
        ArtifactVersionPolicy(
            artifact_name=artifact_name,
            current=CURRENT_ARTIFACT_SCHEMA_VERSION,
            supported=(CURRENT_ARTIFACT_SCHEMA_VERSION,),
            runtime_mode=RUNTIME_VERSION_MODE,
        ),
    )


def assert_supported_artifact_schema_version(
    *,
    payload: dict[str, Any],
    source_name: str,
    artifact_name: str | None = None,
) -> None:
    policy = artifact_version_policy(artifact_name or "<unknown>")
    schema_version = payload.get("schema_version")
    if schema_version not in policy.supported:
        supported = ", ".join(policy.supported)
        raise RuntimeViolation(
            f"{source_name} uses unsupported schema_version {schema_version}; "
            f"supported artifact schema_version for {policy.artifact_name} is {supported}. "
            "Runtime policy is validate_current_refuse_unknown: run scripts/upgrade_artifact.py "
            "before loading old .forgeflow/tasks/* artifacts."
        )


def migrate_artifact_payload(
    *,
    artifact_name: str,
    payload: dict[str, Any],
    source_name: str,
    target_version: str = CURRENT_ARTIFACT_SCHEMA_VERSION,
) -> tuple[dict[str, Any], ArtifactMigrationReport]:
    policy = artifact_version_policy(artifact_name)
    from_version = payload.get("schema_version")
    if target_version != policy.current:
        raise RuntimeViolation(
            f"{source_name} cannot migrate {artifact_name} to {target_version}; "
            f"current supported target is {policy.current}"
        )
    if from_version not in policy.supported:
        raise RuntimeViolation(
            f"{source_name} cannot migrate unsupported schema_version {from_version}; "
            f"supported source versions are {', '.join(policy.supported)}"
        )

    # First-class migration seam. The initial 0.1 -> 0.1 path is intentionally
    # a no-op so future version bumps can add ordered, tested transforms here
    # without changing runtime loader behavior.
    migrated = dict(payload)
    report = ArtifactMigrationReport(
        artifact_name=artifact_name,
        source_name=source_name,
        from_version=str(from_version) if from_version is not None else None,
        to_version=target_version,
        changed=False,
        steps=[f"{from_version}->{target_version} noop"],
    )
    return migrated, report
