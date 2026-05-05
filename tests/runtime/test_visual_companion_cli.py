import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "forgeflow_visual.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_clarify_mermaid_from_brief_json(tmp_path):
    brief = tmp_path / "brief.json"
    brief.write_text(
        json.dumps(
            {
                "task_id": "visual-task",
                "goal": "Add a visual companion",
                "route": "medium",
                "risk_level": "medium",
                "acceptance_criteria": ["CLI renders diagrams", "Web companion can stream updates"],
                "constraints": ["stdlib only for Python helper"],
            }
        ),
        encoding="utf-8",
    )

    result = run_cli("clarify", str(brief), "--format", "mermaid")

    assert result.returncode == 0, result.stderr
    assert "flowchart TD" in result.stdout
    assert "Goal[Goal: Add a visual companion]" in result.stdout
    assert "Route[Route: medium]" in result.stdout
    assert "AC1[AC1: CLI renders diagrams]" in result.stdout
    assert "AC2[AC2: Web companion can stream updates]" in result.stdout


def test_plan_markdown_from_plan_json(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "task_id": "visual-task",
                "steps": [
                    {
                        "id": "step-1",
                        "objective": "Create CLI renderer",
                        "dependencies": [],
                        "expected_output": "CLI prints Mermaid",
                        "verification": "pytest tests/runtime/test_visual_companion_cli.py",
                        "rollback_note": "Remove CLI helper",
                        "fulfills": ["R1"],
                    },
                    {
                        "id": "step-2",
                        "objective": "Document companion server",
                        "dependencies": ["step-1"],
                        "expected_output": "README documents usage",
                        "verification": "manual docs review",
                        "rollback_note": "Revert docs",
                        "fulfills": ["R2"],
                    },
                ],
                "verify_plan": [
                    {"target": "R1", "type": "sub_req", "gates": ["test"]},
                    {"target": "R2", "type": "sub_req", "gates": ["manual_review"]},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_cli("plan", str(plan), "--format", "markdown")

    assert result.returncode == 0, result.stderr
    assert "## ForgeFlow Plan Diagram" in result.stdout
    assert "```mermaid" in result.stdout
    assert "step_1[step-1: Create CLI renderer]" in result.stdout
    assert "step_1 --> step_2" in result.stdout
    assert "### Verification" in result.stdout
    assert "- R1: test" in result.stdout


def test_missing_artifact_fails_clearly(tmp_path):
    result = run_cli("clarify", str(tmp_path / "missing.json"))

    assert result.returncode == 2
    assert "ERROR: artifact not found" in result.stderr


def test_visual_companion_server_has_expected_entrypoints():
    server = ROOT / "scripts" / "visual-companion.cjs"
    text = server.read_text(encoding="utf-8")

    assert "const PORT =" in text
    assert "createServer" in text
    assert "upgrade" in text
    assert "mermaid" in text
    assert "ForgeFlow Visual Companion" in text
