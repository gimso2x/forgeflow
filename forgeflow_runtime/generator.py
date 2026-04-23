from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PROMPT_DIR = REPO_ROOT / "prompts" / "canonical"

ROLE_TO_FILENAME = {
    "coordinator": "coordinator.md",
    "planner": "planner.md",
    "worker": "worker.md",
    "spec-reviewer": "spec-reviewer.md",
    "quality-reviewer": "quality-reviewer.md",
}

DEFAULT_TOKEN_BUDGET = {
    "input": 8000,
    "output": 4000,
}

ROLE_TOKEN_BUDGET_OVERRIDES: dict[str, dict[str, int]] = {
    "planner": {"input": 12000, "output": 6000},
    "spec-reviewer": {"input": 10000, "output": 4000},
    "quality-reviewer": {"input": 10000, "output": 4000},
}


class GenerationError(Exception):
    """Raised when prompt generation cannot satisfy its contract."""


@dataclass(frozen=True)
class PromptContext:
    role: str
    stage: str
    route: str
    task_dir: Path
    task_id: str
    extra_context: dict[str, Any] | None = None


@dataclass(frozen=True)
class GeneratedPrompt:
    role: str
    stage: str
    route: str
    system_prompt: str
    task_prompt: str
    referenced_artifacts: list[str]
    token_budget: dict[str, int]


def _load_role_prompt(role: str) -> str:
    filename = ROLE_TO_FILENAME.get(role)
    if filename is None:
        raise GenerationError(f"unknown role: {role}")
    path = CANONICAL_PROMPT_DIR / filename
    if not path.exists():
        raise GenerationError(f"canonical prompt missing for role {role}: {path}")
    return path.read_text(encoding="utf-8").strip()


def _discover_artifacts(task_dir: Path) -> list[str]:
    if not task_dir.exists():
        return []
    artifacts = []
    for path in sorted(task_dir.iterdir()):
        if path.is_file() and path.suffix == ".json":
            artifacts.append(path.stem)
    return artifacts


def _artifact_summary(task_dir: Path, artifact_name: str) -> str | None:
    path = task_dir / f"{artifact_name}.json"
    if not path.exists():
        return None
    try:
        import json
        payload = json.loads(path.read_text(encoding="utf-8"))
        # Provide a compact summary instead of dumping the whole JSON
        keys = list(payload.keys())[:8]
        preview = json.dumps({k: payload[k] for k in keys}, ensure_ascii=False, indent=2)
        if len(preview) > 1200:
            preview = preview[:1200] + "\n... (truncated)"
        return preview
    except Exception:
        return None


def _token_budget_for_role(role: str) -> dict[str, int]:
    base = dict(DEFAULT_TOKEN_BUDGET)
    override = ROLE_TOKEN_BUDGET_OVERRIDES.get(role)
    if override:
        base.update(override)
    return base


def generate_prompt(ctx: PromptContext) -> GeneratedPrompt:
    """Assemble a full prompt from canonical role + task context + available artifacts."""
    system_prompt = _load_role_prompt(ctx.role)

    lines: list[str] = [
        f"# Task Context",
        f"- task_id: {ctx.task_id}",
        f"- stage: {ctx.stage}",
        f"- route: {ctx.route}",
        f"- role: {ctx.role}",
        "",
    ]

    # Artifact context
    artifacts = _discover_artifacts(ctx.task_dir)
    if artifacts:
        lines.append("## Available Artifacts")
        for name in artifacts:
            summary = _artifact_summary(ctx.task_dir, name)
            if summary:
                lines.append(f"### {name}")
                lines.append(f"```json")
                lines.append(summary)
                lines.append(f"```")
            else:
                lines.append(f"- {name}")
        lines.append("")

    # Extra context
    if ctx.extra_context:
        lines.append("## Extra Context")
        for k, v in ctx.extra_context.items():
            lines.append(f"- {k}: {v}")
        lines.append("")

    lines.append("## Instructions")
    lines.append(f"You are operating as the {ctx.role} for stage `{ctx.stage}`.")
    lines.append("Produce the required artifacts for this stage. Do not skip validation or verification.")

    task_prompt = "\n".join(lines)

    return GeneratedPrompt(
        role=ctx.role,
        stage=ctx.stage,
        route=ctx.route,
        system_prompt=system_prompt,
        task_prompt=task_prompt,
        referenced_artifacts=artifacts,
        token_budget=_token_budget_for_role(ctx.role),
    )
