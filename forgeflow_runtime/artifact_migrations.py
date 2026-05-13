from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from forgeflow_runtime.errors import RuntimeViolation

CURRENT_ARTIFACT_SCHEMA_VERSION = "0.2"
MINIMUM_SUPPORTED_SCHEMA_VERSION = "0.1"
RUNTIME_VERSION_MODE = "validate_and_migrate"


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
        supported=(MINIMUM_SUPPORTED_SCHEMA_VERSION, CURRENT_ARTIFACT_SCHEMA_VERSION),
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
            supported=(MINIMUM_SUPPORTED_SCHEMA_VERSION, CURRENT_ARTIFACT_SCHEMA_VERSION),
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
            f"Runtime policy is {RUNTIME_VERSION_MODE}: "
            "use migrate_artifact_payload() to upgrade old artifacts."
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

    # Ordered migration chain: 0.1 -> 0.2
    migrated = dict(payload)
    steps: list[str] = []
    current_v = str(from_version) if from_version is not None else "0.1"

    if current_v == "0.1" and target_version in ("0.2",):
        migrated = _migrate_0_1_to_0_2(migrated, artifact_name)
        current_v = "0.2"
        steps.append("0.1->0.2")

    changed = from_version != target_version
    report = ArtifactMigrationReport(
        artifact_name=artifact_name,
        source_name=source_name,
        from_version=str(from_version) if from_version is not None else None,
        to_version=target_version,
        changed=changed,
        steps=steps if steps else [f"{from_version}->{target_version} noop"],
    )
    return migrated, report


def _migrate_0_1_to_0_2(payload: dict[str, Any], artifact_name: str) -> dict[str, Any]:
    """Migrate artifact from schema_version 0.1 to 0.2.

    Changes in 0.2:
    - review-report: add review_roles, review_type expanded (security, ux)
    - brief: add required_specialists, skipped_specialists, skip_rationale
    - All: bump schema_version to "0.2"
    """
    migrated = dict(payload)
    migrated["schema_version"] = "0.2"

    if artifact_name in ("review-report", "review-report-spec", "review-report-quality"):
        migrated.setdefault("review_type", "quality")
        if "review_roles" not in migrated:
            migrated["review_roles"] = ["spec-review", "quality-review"]

    if artifact_name == "brief":
        if "required_specialists" not in migrated:
            migrated["required_specialists"] = []
        if "skipped_specialists" not in migrated:
            migrated["skipped_specialists"] = []
        if "skip_rationale" not in migrated:
            migrated["skip_rationale"] = ""

    return migrated
