"""Tests for forgeflow_runtime.evidence_qa."""

from __future__ import annotations

import dataclasses
import sys

import pytest

from forgeflow_runtime.evidence_qa import (
    EvidenceContract,
    ProjectType,
    QAScenario,
    detect_project_type,
    run_evidence_contract,
    run_qa_cycle,
    select_scenarios,
    summarize_qa_results,
)


# ---------------------------------------------------------------------------
# Frozen immutability
# ---------------------------------------------------------------------------

class TestFrozenImmutability:
    def test_qa_scenario_is_frozen(self) -> None:
        s = QAScenario(
            name="test",
            description="d",
            command="echo hi",
            repair_command=None,
            required_for={ProjectType.APP},
            evidence_keys={"a"},
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            s.name = "changed"  # type: ignore[misc]

    def test_evidence_contract_is_frozen(self) -> None:
        c = EvidenceContract(
            scenario_name="test",
            status="pass",
            executed=True,
            coverage=1.0,
            console_errors=[],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.status = "fail"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# detect_project_type
# ---------------------------------------------------------------------------

class TestDetectProjectType:
    def test_package_json_is_app(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "package.json").write_text("{}")
        assert detect_project_type(str(p)) is ProjectType.APP

    def test_requirements_txt_is_app(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "requirements.txt").write_text("")
        assert detect_project_type(str(p)) is ProjectType.APP

    def test_dockerfile_is_service(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "Dockerfile").write_text("FROM alpine")
        assert detect_project_type(str(p)) is ProjectType.SERVICE

    def test_docker_compose_is_service(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "docker-compose.yml").write_text("services: {}")
        assert detect_project_type(str(p)) is ProjectType.SERVICE

    def test_migrations_dir_is_database(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "migrations").mkdir()
        assert detect_project_type(str(p)) is ProjectType.DATABASE

    def test_sql_files_is_database(self, tmp_path: object) -> None:
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "init.sql").write_text("SELECT 1")
        assert detect_project_type(str(p)) is ProjectType.DATABASE

    def test_empty_dir_is_unknown(self, tmp_path: object) -> None:
        assert detect_project_type(str(tmp_path)) is ProjectType.UNKNOWN

    def test_database_wins_over_app(self, tmp_path: object) -> None:
        """DATABASE has higher priority than APP."""
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "migrations").mkdir()
        (p / "package.json").write_text("{}")
        assert detect_project_type(str(p)) is ProjectType.DATABASE

    def test_service_wins_over_app(self, tmp_path: object) -> None:
        """SERVICE has higher priority than APP."""
        from pathlib import Path
        p = Path(tmp_path)  # type: ignore[arg-type]
        (p / "Dockerfile").write_text("FROM alpine")
        (p / "package.json").write_text("{}")
        assert detect_project_type(str(p)) is ProjectType.SERVICE


# ---------------------------------------------------------------------------
# select_scenarios
# ---------------------------------------------------------------------------

class TestSelectScenarios:
    def test_app_scenarios(self) -> None:
        names = {s.name for s in select_scenarios(ProjectType.APP)}
        assert names == {
            "ui-button-event",
            "modal-popup",
            "confirm-dialog",
            "alert-dialog",
            "browser-console-clean",
        }

    def test_service_scenarios(self) -> None:
        names = {s.name for s in select_scenarios(ProjectType.SERVICE)}
        assert names == {"browser-console-clean", "api-flow"}

    def test_database_scenarios(self) -> None:
        names = {s.name for s in select_scenarios(ProjectType.DATABASE)}
        assert names == {"api-flow", "database-state"}

    def test_unknown_returns_empty(self) -> None:
        assert select_scenarios(ProjectType.UNKNOWN) == []


# ---------------------------------------------------------------------------
# run_evidence_contract
# ---------------------------------------------------------------------------

class TestRunEvidenceContract:
    def test_valid_json_pass(self) -> None:
        scenario = QAScenario(
            name="valid-pass",
            description="d",
            command=(
                f"{sys.executable} -c \"import json; print(json.dumps({{'status':'pass','executed':True,'coverage':0.9,'console_errors':[]}}))\""
            ),
            repair_command=None,
            required_for={ProjectType.APP},
            evidence_keys={"a"},
        )
        contract = run_evidence_contract(scenario)
        assert contract.status == "pass"
        assert contract.executed is True
        assert contract.coverage == 0.9
        assert contract.console_errors == []

    def test_non_json_fails(self) -> None:
        scenario = QAScenario(
            name="bad-output",
            description="d",
            command="echo not-json",
            repair_command=None,
            required_for={ProjectType.APP},
            evidence_keys={"a"},
        )
        contract = run_evidence_contract(scenario)
        assert contract.status == "fail"
        assert contract.executed is False


# ---------------------------------------------------------------------------
# run_qa_cycle
# ---------------------------------------------------------------------------

class TestRunQACycle:
    def test_returns_correct_count(self) -> None:
        scenarios = select_scenarios(ProjectType.APP)
        contracts = run_qa_cycle(scenarios)
        assert len(contracts) == len(scenarios)
        assert all(isinstance(c, EvidenceContract) for c in contracts)


# ---------------------------------------------------------------------------
# summarize_qa_results
# ---------------------------------------------------------------------------

class TestSummarizeQAResults:
    def test_pass_rate(self) -> None:
        contracts = [
            EvidenceContract("a", "pass", True, 1.0, []),
            EvidenceContract("b", "pass", True, 1.0, []),
            EvidenceContract("c", "fail", True, 0.5, ["err"]),
        ]
        result = summarize_qa_results(contracts)
        assert result["total"] == 3
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["skipped"] == 0
        assert result["pass_rate"] == pytest.approx(2 / 3)

    def test_empty_contracts(self) -> None:
        result = summarize_qa_results([])
        assert result["total"] == 0
        assert result["pass_rate"] == 0.0
