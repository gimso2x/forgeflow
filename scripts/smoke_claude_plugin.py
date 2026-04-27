#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

DRY_RUN_CASES = [
    (
        "clarify_exact",
        "/forgeflow:clarify Dry run only. Return only one selected route label for: fix one README typo. Valid labels: small, medium, large_high_risk. Do not write files. Do not run commands.",
        "label",
    ),
    (
        "specify_exact",
        "/forgeflow:specify Dry run only. Your entire response must be exactly two numbered lines and nothing else: no preamble, no heading, no summary. List two spec questions for a README badge task. Do not write files. Do not run commands.",
        "two_lines",
    ),
    (
        "plan_exact",
        "/forgeflow:plan Dry run only. Your entire response must be exactly two numbered lines and nothing else: no preamble, no heading, no summary. List two plan steps for a README badge task. Do not write files. Do not run commands.",
        "two_lines",
    ),
    (
        "run_exact",
        "/forgeflow:run Dry run only. Your entire response must be exactly two numbered lines and nothing else: no preamble, no heading, no summary. List two execution checks for a README badge task. Do not write files. Do not run commands.",
        "two_lines",
    ),
    (
        "review_exact",
        "/forgeflow:review Dry run only. Your entire response must be exactly two numbered lines and nothing else: no preamble, no heading, no summary. For a README badge diff, list two review checks. Do not write files. Do not run commands.",
        "two_lines",
    ),
    (
        "ship_exact",
        "/forgeflow:ship Dry run only. Your entire response must be exactly two numbered lines and nothing else: no preamble, no heading, no summary. List two ship checks for a README badge task. Do not write files. Do not run commands.",
        "two_lines",
    ),
]


def run_claude(prompt: str, out_dir: Path, name: str, timeout: int) -> dict:
    raw_path = out_dir / f"{name}.raw"
    json_path = out_dir / f"{name}.json"
    command = [
        "script",
        "-qfec",
        f"claude --dangerously-skip-permissions -p {sh_quote(prompt)} --output-format json",
        "/dev/null",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    raw_path.write_text(completed.stdout, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise AssertionError(f"{name}: claude exited {completed.returncode}; see {raw_path}")
    raw = ANSI_RE.sub("", completed.stdout)
    objects = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                objects.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass
    if not objects:
        raise AssertionError(f"{name}: no JSON result found; see {raw_path}")
    result = objects[-1]
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def assert_no_permission_denials(name: str, result: dict) -> None:
    denials = result.get("permission_denials")
    if denials != []:
        raise AssertionError(f"{name}: expected permission_denials=[]; got {denials!r}")


def assert_exact_label(name: str, text: str) -> None:
    if text.strip() not in {"small", "medium", "large_high_risk"}:
        raise AssertionError(f"{name}: expected only route label; got {text!r}")


def assert_two_numbered_lines(name: str, text: str) -> None:
    stripped = text.strip()
    if "```" in stripped:
        raise AssertionError(f"{name}: code fence is forbidden; got {text!r}")
    lines = [line.rstrip() for line in stripped.splitlines() if line.strip()]
    if len(lines) != 2:
        raise AssertionError(f"{name}: expected exactly 2 non-empty lines; got {len(lines)}: {lines!r}")
    if not lines[0].lstrip().startswith("1.") or not lines[1].lstrip().startswith("2."):
        raise AssertionError(f"{name}: expected numbered lines starting 1./2.; got {lines!r}")


def validate_schema(task_dir: Path, artifact: str, schema: str) -> None:
    data_path = task_dir / artifact
    if not data_path.exists():
        raise AssertionError(f"missing artifact: {data_path}")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    schema_data = json.loads((ROOT / "schemas" / schema).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema_data).iter_errors(data), key=lambda err: list(err.path))
    if errors:
        details = "; ".join(f"{'.'.join(map(str, err.path)) or '<root>'}: {err.message}" for err in errors)
        raise AssertionError(f"{artifact} schema failed: {details}")


def assert_init_artifacts(task_dir: Path) -> None:
    expected = ["brief.json", "run-state.json", "checkpoint.json", "session-state.json"]
    missing = [name for name in expected if not (task_dir / name).exists()]
    if missing:
        raise AssertionError(f"init_write missing starter artifacts: {missing}")
    for name in expected:
        json.loads((task_dir / name).read_text(encoding="utf-8"))


def git_status() -> str:
    return subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test installed ForgeFlow Claude plugin slash skills.")
    parser.add_argument("--timeout", type=int, default=180, help="per-Claude-call timeout seconds")
    parser.add_argument("--keep-temp", action="store_true", help="keep temporary output directories")
    args = parser.parse_args()

    if not shutil.which("claude"):
        print("CLAUDE PLUGIN SMOKE: SKIP - claude CLI not found")
        return 77
    if not shutil.which("script"):
        print("CLAUDE PLUGIN SMOKE: SKIP - script command not found")
        return 77

    before_status = git_status()
    out_dir = Path(tempfile.mkdtemp(prefix="forgeflow-claude-plugin-smoke-"))
    task_dir = Path(tempfile.mkdtemp(prefix="forgeflow-claude-plugin-task-"))
    errors: list[str] = []

    try:
        for name, prompt, assertion in DRY_RUN_CASES:
            print(f"== {name} ==")
            result = run_claude(prompt, out_dir, name, args.timeout)
            assert_no_permission_denials(name, result)
            text = result.get("result", "")
            if assertion == "label":
                assert_exact_label(name, text)
            else:
                assert_two_numbered_lines(name, text)
            print(text.strip())

        write_cases = [
            (
                "init_write",
                f"/forgeflow:init --task-id claude-plugin-smoke --objective \"Smoke-test init slash command\" --risk low --task-dir {task_dir}. Create only the init starter artifacts in that task directory. Do not modify repository files outside that task directory.",
            ),
            (
                "plan_write",
                f"/forgeflow:plan Write plan.json under {task_dir} for a README badge task. Keep it minimal. Use schema_version exactly 0.1. Do not modify repository files outside that task directory.",
            ),
            (
                "review_write",
                f"/forgeflow:review Write review-report.json under {task_dir} for a hypothetical README badge diff. Keep it minimal. Use schema_version exactly 0.1. Do not modify repository files outside that task directory.",
            ),
        ]
        for name, prompt in write_cases:
            print(f"== {name} ==")
            result = run_claude(prompt, out_dir, name, args.timeout)
            assert_no_permission_denials(name, result)
            print(result.get("result", "").strip())

        assert_init_artifacts(task_dir)
        validate_schema(task_dir, "plan.json", "plan.schema.json")
        validate_schema(task_dir, "review-report.json", "review-report.schema.json")
        print("init_artifacts=PASS")
        print("plan_schema=PASS")
        print("review-report_schema=PASS")

        after_status = git_status()
        if after_status != before_status:
            raise AssertionError(f"repo dirty-state changed during smoke\nbefore:\n{before_status}\nafter:\n{after_status}")

        print(f"OUT_DIR={out_dir}")
        print(f"TASK_DIR={task_dir}")
        print("CLAUDE PLUGIN SMOKE: PASS")
        return 0
    except Exception as exc:  # noqa: BLE001 - command-line smoke should print concise failure.
        errors.append(str(exc))
        print("CLAUDE PLUGIN SMOKE: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(f"OUT_DIR={out_dir}", file=sys.stderr)
        print(f"TASK_DIR={task_dir}", file=sys.stderr)
        return 1
    finally:
        if not args.keep_temp:
            shutil.rmtree(task_dir, ignore_errors=True)
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
