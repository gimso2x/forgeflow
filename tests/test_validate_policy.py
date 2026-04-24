import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_POLICY_PATH = ROOT / "scripts" / "validate_policy.py"


def _load_validate_policy_module():
    spec = importlib.util.spec_from_file_location("validate_policy", VALIDATE_POLICY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_policy_passes_repo_policy() -> None:
    validate_policy = _load_validate_policy_module()

    errors = validate_policy.validate_policy_root(ROOT)

    assert errors == []


def test_repo_policy_defines_self_evolution_ssot() -> None:
    validate_policy = _load_validate_policy_module()

    evolution = validate_policy._load_yaml(ROOT / "policy" / "canonical" / "evolution.yaml")

    assert evolution["scope"] == "project-local"
    assert evolution["default_artifact_root"] == ".forgeflow/evolution"
    assert "global_user_scope" in evolution["forbidden_targets"]
    assert evolution["authority"] == ["eval-record", "decision-log", "review-report", "run-state"]


def test_validate_policy_rejects_structurally_invalid_yaml_fixture(tmp_path: Path) -> None:
    validate_policy = _load_validate_policy_module()
    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    policy_dir = fixture_root / "policy" / "canonical"
    policy_dir.mkdir(parents=True)
    docs_dir = fixture_root / "docs"
    docs_dir.mkdir()
    schemas_dir = fixture_root / "schemas"
    schemas_dir.mkdir()
    policy_schema_dir = schemas_dir / "policy"
    policy_schema_dir.mkdir()

    (policy_dir / "workflow.yaml").write_text(
        """version: 0.1
stages:
  - clarify
  - plan
  - execute
  - spec-review
  - quality-review
  - finalize
  - long-run
review_order:
  - spec-review
  - quality-review
""",
        encoding="utf-8",
    )
    (policy_dir / "stages.yaml").write_text(
        """stages:
  clarify:
    required_for_entry: [brief]
  plan:
    required_for_entry: [brief, plan]
  execute:
    required_for_entry: [brief]
  spec-review:
    required_for_entry: [run-state]
  quality-review:
    required_for_entry: [run-state]
  finalize:
    required_for_entry: [run-state]
  long-run:
    required_for_entry: [eval-record]
""",
        encoding="utf-8",
    )
    (policy_dir / "gates.yaml").write_text(
        """version: 0.2
gates:
  clarification_complete:
    requires: brief
  plan_executable:
    requires: [plan]
  execution_evidenced:
    requires: [decision-log, run-state]
  spec_review_passed:
    requires: [review-report]
    review_type: spec
    verdict: approved
  quality_review_passed:
    requires: [review-report]
    review_type: quality
    verdict: approved
  ready_to_finalize:
    requires: [run-state]
    run_state_flags: [spec_review_approved, quality_review_approved]
  worth_long_run_capture:
    requires: [eval-record]
""",
        encoding="utf-8",
    )
    (policy_dir / "complexity-routing.yaml").write_text(
        """version: 0.1
routes:
  small:
    stages: [clarify, execute, quality-review, finalize]
  medium:
    stages: [clarify, plan, execute, quality-review, finalize]
  large_high_risk:
    stages: [clarify, plan, execute, spec-review, quality-review, finalize, long-run]
""",
        encoding="utf-8",
    )
    (policy_dir / "evolution.yaml").write_text(
        """version: 0.1
scope: project-local
default_artifact_root: .forgeflow/evolution
authority: [eval-record, decision-log, review-report, run-state]
triggers: [repeated failure pattern with evidence]
non_negotiables:
  - self-evolution must be proposed from project-local artifacts, not chat vibes
  - no global user-scope writes by default
  - every proposed harness change needs verification evidence before adoption
forbidden_targets: [global_user_scope]
outputs: [evolution-proposal, verification-evidence, decision-log]
""",
        encoding="utf-8",
    )
    (docs_dir / "review-model.md").write_text(
        "spec-review 승인 전 finalize 금지\nquality-review 승인 전 high-risk finalize 금지\nrun-state.spec_review_approved\n",
        encoding="utf-8",
    )

    for schema_name in ["brief", "plan", "decision-log", "run-state", "review-report", "eval-record"]:
        (schemas_dir / f"{schema_name}.schema.json").write_text(
            '{"type":"object","required":["schema_version","task_id"]}', encoding="utf-8"
        )

    for policy_schema_name in ["workflow", "stages", "gates", "complexity-routing", "evolution"]:
        (policy_schema_dir / f"{policy_schema_name}.schema.json").write_text(
            (ROOT / "schemas" / "policy" / f"{policy_schema_name}.schema.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    errors = validate_policy.validate_policy_root(fixture_root)

    assert any("gates.yaml failed schema validation" in error for error in errors)
