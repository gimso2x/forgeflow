from unittest.mock import Mock, patch

from forgeflow_runtime.artifact_validation import validate_artifact_payload
from forgeflow_runtime.natural_language_plan import generate_plan_from_issue, generate_plan_from_text, github_issue_text, validate_plan_draft


def test_generate_plan_from_text_maps_requirements_to_schema_valid_steps():
    draft = generate_plan_from_text(
        "task-natural-plan",
        """
        The system shall add a smoke-test badge to the home page.
        WHEN lint runs THEN the system SHALL pass without warnings.
        """,
        issue_refs=["#101"],
    )

    assert draft.template == "new_feature"
    assert draft.quality["ok"] is True
    assert draft.quality["step_count"] == 2
    assert draft.plan["task_id"] == "task-natural-plan"
    assert draft.plan["steps"][0]["fulfills"] == ["REQ-001"]
    assert draft.plan["steps"][1]["dependencies"] == ["step-1"]
    assert "#101" in draft.plan["steps"][0]["expected_output"]
    validate_artifact_payload(artifact_name="plan", payload=draft.plan, source_name="generated-plan")


def test_generate_plan_from_text_selects_bugfix_template_and_verification():
    draft = generate_plan_from_text(
        "fix-login",
        "Fix the login regression. The system shall reject expired sessions. Add a regression test.",
    )

    assert draft.template == "bugfix"
    assert any("regression test" in step["verification"].lower() for step in draft.plan["steps"])
    assert draft.quality["missing_requirements"] == []
    validate_artifact_payload(artifact_name="plan", payload=draft.plan, source_name="bugfix-plan")


def test_validate_plan_draft_reports_missing_coverage():
    quality = validate_plan_draft(
        {
            "schema_version": "0.1",
            "task_id": "incomplete",
            "steps": [
                {
                    "id": "step-1",
                    "objective": "Do one thing",
                    "expected_output": "Output exists",
                    "verification": "Run test",
                    "fulfills": ["REQ-001"],
                    "dependencies": ["missing-step"],
                }
            ],
            "verify_plan": [],
        },
        requirement_ids=["REQ-001", "REQ-002"],
    )

    assert quality["ok"] is False
    assert quality["missing_requirements"] == ["REQ-002"]
    assert quality["missing_verification"] == ["REQ-001", "REQ-002"]
    assert quality["unknown_dependencies"] == ["missing-step"]


def test_github_issue_text_collects_title_body_and_trace_ref():
    completed = Mock(stdout='{"number": 101, "title": "Plan generator", "body": "The system shall plan."}')

    with patch("forgeflow_runtime.natural_language_plan.subprocess.run", return_value=completed) as run:
        text, refs = github_issue_text("#101", repo="owner/repo")

    assert text == "Plan generator\n\nThe system shall plan."
    assert refs == ["#101"]
    run.assert_called_once_with(
        ["gh", "issue", "view", "101", "--json", "number,title,body", "--repo", "owner/repo"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_generate_plan_from_issue_preserves_issue_ref():
    with patch("forgeflow_runtime.natural_language_plan.github_issue_text", return_value=("The system shall create a plan.", ["#101"])):
        draft = generate_plan_from_issue("issue-plan", 101)

    assert draft.quality["ok"] is True
    assert "#101" in draft.plan["steps"][0]["expected_output"]
