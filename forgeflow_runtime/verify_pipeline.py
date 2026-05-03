"""Verification-driven pipeline for ForgeFlow.

Provides a structured verify → fix → retry loop with optional spec-review
gate.  Results are collected as :class:`VerifyResult` instances and can be
summarized or formatted into a human-readable report.

No external dependencies beyond the Python standard library.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class VerifyStage(str, Enum):
    """Stages in the verification pipeline."""

    SPEC_REVIEW = "SPEC_REVIEW"
    VERIFY = "VERIFY"
    FIX = "FIX"
    PASS = "PASS"


@dataclass(frozen=True)
class VerifyResult:
    """Immutable result of a single verification / fix step."""

    stage: VerifyStage
    passed: bool
    evidence: str
    attempt: int = 1
    fix_applied: bool = False


@dataclass(frozen=True)
class VerifyConfig:
    """Configuration for the verification loop."""

    verify_command: str
    max_attempts: int = 3
    fix_command: str | None = None
    spec_review_command: str | None = None


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def run_verify_step(command: str, timeout: int = 120) -> VerifyResult:
    """Run *command* via subprocess and return a :class:`VerifyResult`.

    Exit code 0 → ``passed=True``, any non-zero → ``passed=False``.
    """
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
        )
        evidence = (proc.stdout or "") + (proc.stderr or "")
        passed = proc.returncode == 0
    except subprocess.TimeoutExpired as exc:
        evidence = f"Command timed out after {timeout}s"
        passed = False
    except Exception as exc:
        evidence = f"Exception running command: {exc}"
        passed = False

    return VerifyResult(stage=VerifyStage.VERIFY, passed=passed, evidence=evidence.strip())


def run_fix_step(command: str, timeout: int = 120) -> VerifyResult:
    """Run a fix command and return a :class:`VerifyResult` with ``FIX`` stage."""
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
        )
        evidence = (proc.stdout or "") + (proc.stderr or "")
        passed = proc.returncode == 0
    except subprocess.TimeoutExpired as exc:
        evidence = f"Fix timed out after {timeout}s"
        passed = False
    except Exception as exc:
        evidence = f"Exception running fix: {exc}"
        passed = False

    return VerifyResult(stage=VerifyStage.FIX, passed=passed, evidence=evidence.strip(), fix_applied=True)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_verification_loop(config: VerifyConfig) -> list[VerifyResult]:
    """Execute the verify → fix → retry loop according to *config*.

    1. If *spec_review_command* is set, run it first.  Failure stops the loop.
    2. Run *verify_command*.  Pass → return single ``PASS`` result.
    3. On failure, run *fix_command* (if provided) and retry verify up to
       *max_attempts* total attempts.
    """
    results: list[VerifyResult] = []

    # --- optional spec-review gate ---
    if config.spec_review_command is not None:
        spec_proc = subprocess.run(
            config.spec_review_command,
            capture_output=True,
            text=True,
            shell=True,
            timeout=120,
        )
        spec_passed = spec_proc.returncode == 0
        spec_evidence = ((spec_proc.stdout or "") + (spec_proc.stderr or "")).strip()
        spec_result = VerifyResult(stage=VerifyStage.SPEC_REVIEW, passed=spec_passed, evidence=spec_evidence)
        results.append(spec_result)
        if not spec_passed:
            return results

    # --- verify / fix loop ---
    for attempt in range(1, config.max_attempts + 1):
        vr = run_verify_step(config.verify_command)
        if vr.passed:
            results.append(VerifyResult(
                stage=VerifyStage.PASS,
                passed=True,
                evidence=vr.evidence,
                attempt=attempt,
            ))
            return results

        # verification failed — record the failure
        results.append(VerifyResult(
            stage=VerifyStage.VERIFY,
            passed=False,
            evidence=vr.evidence,
            attempt=attempt,
        ))

        if config.fix_command is not None:
            fix_result = run_fix_step(config.fix_command)
            results.append(VerifyResult(
                stage=VerifyStage.FIX,
                passed=fix_result.passed,
                evidence=fix_result.evidence,
                attempt=attempt,
                fix_applied=True,
            ))

    return results


# ---------------------------------------------------------------------------
# Summary & reporting
# ---------------------------------------------------------------------------

def summarize_verify_results(results: list[VerifyResult]) -> dict[str, Any]:
    """Return a summary dict of verification results."""
    stages_run = [r.stage.value for r in results]
    fix_count = sum(1 for r in results if r.stage == VerifyStage.FIX)
    final_passed = results[-1].passed if results else False
    total_attempts = sum(1 for r in results if r.stage in (VerifyStage.VERIFY, VerifyStage.PASS))

    return {
        "total_attempts": total_attempts,
        "final_passed": final_passed,
        "stages_run": stages_run,
        "fix_count": fix_count,
    }


def format_verify_report(results: list[VerifyResult]) -> str:
    """Format verification results into a human-readable report."""
    if not results:
        return "No verification results."

    lines: list[str] = []
    lines.append("=== Verification Report ===")
    for i, r in enumerate(results, 1):
        status = "PASS" if r.passed else "FAIL"
        fix_tag = " [fix applied]" if r.fix_applied else ""
        lines.append(f"  {i}. [{r.stage.value}] {status} (attempt {r.attempt}){fix_tag}")
        if r.evidence:
            lines.append(f"     Evidence: {r.evidence}")

    summary = summarize_verify_results(results)
    lines.append("--- Summary ---")
    lines.append(f"  Total attempts: {summary['total_attempts']}")
    lines.append(f"  Final passed: {summary['final_passed']}")
    lines.append(f"  Stages run: {', '.join(summary['stages_run'])}")
    lines.append(f"  Fix count: {summary['fix_count']}")

    return "\n".join(lines)
