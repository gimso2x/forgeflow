from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "policy/canonical/team-patterns.yaml"
GENERATED = {
    "claude": ROOT / "adapters/generated/claude/CLAUDE.md",
    "codex": ROOT / "adapters/generated/codex/CODEX.md",
    "cursor": ROOT / "adapters/generated/cursor/HARNESS_CURSOR.md",
}

REQUIRED_PATTERNS = {
    "pipeline",
    "fanout_fanin",
    "expert_pool",
    "producer_reviewer",
    "supervisor",
    "hierarchical_delegation",
    "hybrid",
}
REQUIRED_FIELDS = {
    "summary",
    "when_to_use",
    "avoid_when",
    "parallelism",
    "coordination_cost",
    "required_artifacts",
    "recommended_review_gate",
    "adapter_delivery",
}


def test_canonical_team_pattern_contract_exists_with_required_patterns():
    data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert data["title"] == "ForgeFlow Team Pattern Contract"
    assert set(data["patterns"]) == REQUIRED_PATTERNS
    for name, pattern in data["patterns"].items():
        assert REQUIRED_FIELDS <= set(pattern), name
        assert pattern["when_to_use"], name
        assert pattern["avoid_when"], name
        assert pattern["required_artifacts"], name
        assert pattern["recommended_review_gate"] in {
            "quality-review",
            "spec-review + quality-review",
            "incremental quality-review",
        }


def test_team_pattern_contract_stays_adapter_neutral():
    text = CONTRACT.read_text(encoding="utf-8")
    forbidden_runtime_primitives = ["TeamCreate", "SendMessage", "TaskCreate", ".claude/agents"]
    for primitive in forbidden_runtime_primitives:
        assert primitive not in text


def test_generated_adapters_include_team_pattern_guidance():
    contract_text = CONTRACT.read_text(encoding="utf-8").strip()
    for target, path in GENERATED.items():
        text = path.read_text(encoding="utf-8")
        assert "## Team pattern guidance" in text, target
        assert "Use these patterns to choose orchestration shape; do not treat them as target-specific runtime primitives." in text, target
        assert contract_text in text, target
