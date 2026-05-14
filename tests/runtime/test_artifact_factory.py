import pytest

def test_artifact_factory_brief(artifact_factory, assert_schema_valid):
    brief = artifact_factory("brief", task_id="test-task")
    assert brief["task_id"] == "test-task"
    assert brief["schema_version"] == "0.2"
    assert_schema_valid("brief", brief)

def test_artifact_factory_invalid_type(artifact_factory):
    with pytest.raises(ValueError, match="Unknown artifact type"):
        artifact_factory("non-existent")
