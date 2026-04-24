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


def test_repo_policy_defines_global_advisory_project_enforcement_evolution_ssot() -> None:
    validate_policy = _load_validate_policy_module()

    evolution = validate_policy._load_yaml(ROOT / "policy" / "canonical" / "evolution.yaml")

    assert evolution["scopes"]["global"]["activation"] == "explicit_opt_in"
    assert evolution["scopes"]["global"]["artifact_root"] == "${FORGEFLOW_EVOLUTION_HOME:-~/.forgeflow/evolution}"
    assert "learn_metadata_patterns" in evolution["scopes"]["global"]["permissions"]
    assert "hard_enforcement_by_default" in evolution["scopes"]["global"]["forbidden"]
    assert "raw_prompt_storage_by_default" in evolution["scopes"]["global"]["forbidden"]
    assert "raw_frustration_text_by_default" in evolution["scopes"]["global"]["forbidden"]
    assert "cross_project_exit_2" in evolution["scopes"]["global"]["forbidden"]
    assert "advise_review" not in evolution["scopes"]["global"]["permissions"]

    assert evolution["scopes"]["project"]["artifact_root"] == ".forgeflow/evolution"
    assert "enforce_adopted_hard_rules" in evolution["scopes"]["project"]["permissions"]
    assert evolution["rule_lifecycle"] == ["candidate", "soft", "hard_candidate", "adopted_hard", "retired"]
    assert "adopted_soft" not in evolution["rule_lifecycle"]
    assert "user_frustration_label" in evolution["signal_sources"]
    assert evolution["retrieval_contract"]["max_patterns"] == 3
    assert set(evolution["retrieval_contract"]["requires"]) == {"confidence", "why_matched", "scope", "source_count"}
    assert "project_local_enablement" in evolution["scopes"]["project"]["hard_gate_requires"]
    assert "independent_recurrence_or_audited_maintainer_enablement" in evolution["scopes"]["project"]["hard_gate_requires"]
    assert "low_false_positive_rate" in evolution["scopes"]["project"]["hard_gate_requires"]


def test_validate_policy_rejects_global_review_advice_boundary_violation(tmp_path: Path) -> None:
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

    for name in ["workflow", "stages", "gates", "complexity-routing"]:
        (policy_dir / f"{name}.yaml").write_text(
            (ROOT / "policy" / "canonical" / f"{name}.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    evolution = (ROOT / "policy" / "canonical" / "evolution.yaml").read_text(encoding="utf-8")
    (policy_dir / "evolution.yaml").write_text(
        evolution.replace("      - advise_plan\n", "      - advise_plan\n      - advise_review\n"),
        encoding="utf-8",
    )

    for schema_name in ["brief", "plan", "decision-log", "run-state", "review-report", "eval-record"]:
        (schemas_dir / f"{schema_name}.schema.json").write_text(
            (ROOT / "schemas" / f"{schema_name}.schema.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
    for policy_schema_name in ["workflow", "stages", "gates", "complexity-routing", "evolution"]:
        (policy_schema_dir / f"{policy_schema_name}.schema.json").write_text(
            (ROOT / "schemas" / "policy" / f"{policy_schema_name}.schema.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    for doc_name in ["review-model.md", "long-run-model.md"]:
        (docs_dir / doc_name).write_text((ROOT / "docs" / doc_name).read_text(encoding="utf-8"), encoding="utf-8")

    errors = validate_policy.validate_policy_root(fixture_root)

    assert any("advise_review" in error for error in errors)


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
        """version: 0.2
scopes:
  global:
    artifact_root: ${FORGEFLOW_EVOLUTION_HOME:-~/.forgeflow/evolution}
    activation: explicit_opt_in
    permissions: [learn_metadata_patterns, advise_clarify, advise_plan]
    forbidden: [raw_prompt_storage_by_default, raw_frustration_text_by_default, hard_enforcement_by_default, cross_project_exit_2]
  project:
    artifact_root: .forgeflow/evolution
    permissions: [adopt_rules, verify_rules, enforce_adopted_hard_rules, store_raw_evidence]
    hard_gate_requires: [project_local_enablement, soft_soak_period, independent_recurrence_or_audited_maintainer_enablement, deterministic_check, low_false_positive_rate, rollback_available, eval_record, audit_trail]
rule_lifecycle: [candidate, soft, hard_candidate, adopted_hard, retired]
signal_sources: [fix_commit, review_finding, eval_failure, repeated_tool_failure, user_frustration_label, manual_operator_note]
retrieval_contract:
  max_patterns: 3
  requires: [confidence, why_matched, scope, source_count]
non_negotiables:
  - global learns metadata and advises but must not block by default
  - raw evidence stays project-local unless explicitly redacted and exported
  - project-local adoption is required before HARD enforcement
  - user frustration is a signal label, not standalone evidence or raw global text
  - generated adapters are regenerated from canonical sources, not hand-edited
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
