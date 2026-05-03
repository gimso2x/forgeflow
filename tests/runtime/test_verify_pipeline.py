"""Tests for the verification-driven pipeline."""

from __future__ import annotations

from forgeflow_runtime.verify_pipeline import (
    VerifyConfig,
    VerifyResult,
    VerifyStage,
    format_verify_report,
    run_verification_loop,
    run_verify_step,
    summarize_verify_results,
)


# ---------------------------------------------------------------------------
# run_verify_step
# ---------------------------------------------------------------------------

class TestRunVerifyStep:
    def test_exit_zero_passed(self) -> None:
        result = run_verify_step("echo hello")
        assert result.passed is True
        assert "hello" in result.evidence

    def test_nonzero_exit_failed(self) -> None:
        result = run_verify_step("exit 1")
        assert result.passed is False

    def test_stderr_captured(self) -> None:
        result = run_verify_step("echo oops >&2; exit 1")
        assert result.passed is False
        assert "oops" in result.evidence


# ---------------------------------------------------------------------------
# VerifyConfig defaults
# ---------------------------------------------------------------------------

class TestVerifyConfig:
    def test_defaults(self) -> None:
        cfg = VerifyConfig(verify_command="true")
        assert cfg.max_attempts == 3
        assert cfg.fix_command is None
        assert cfg.spec_review_command is None


# ---------------------------------------------------------------------------
# run_verification_loop — passing scenarios
# ---------------------------------------------------------------------------

class TestVerifyLoopPass:
    def test_pass_on_first_try(self) -> None:
        cfg = VerifyConfig(verify_command="echo ok")
        results = run_verification_loop(cfg)
        assert len(results) == 1
        assert results[0].stage == VerifyStage.PASS
        assert results[0].passed is True
        assert results[0].attempt == 1


# ---------------------------------------------------------------------------
# run_verification_loop — fail + fix + pass
# ---------------------------------------------------------------------------

class TestVerifyLoopFixPass:
    def test_fail_fix_pass(self) -> None:
        """Verify fails attempt 1, fix runs, verify passes attempt 2."""
        # Use a temp file as a state flag: first verify fails, fix touches it,
        # second verify succeeds.
        import tempfile, os

        with tempfile.TemporaryDirectory() as tmpdir:
            flag = os.path.join(tmpdir, "flag")
            verify_cmd = f"test -f {flag} && echo ok"
            fix_cmd = f"touch {flag}"

            cfg = VerifyConfig(
                verify_command=verify_cmd,
                fix_command=fix_cmd,
                max_attempts=3,
            )
            results = run_verification_loop(cfg)
        # Should get: VERIFY(FAIL), FIX, PASS
        stages = [r.stage for r in results]
        assert len(results) == 3
        assert stages[0] == VerifyStage.VERIFY
        assert not results[0].passed
        assert stages[1] == VerifyStage.FIX
        assert stages[2] == VerifyStage.PASS
        assert results[2].passed is True


# ---------------------------------------------------------------------------
# run_verification_loop — max attempts exhausted
# ---------------------------------------------------------------------------

class TestVerifyLoopExhausted:
    def test_max_attempts_exhausted(self) -> None:
        cfg = VerifyConfig(
            verify_command="exit 1",
            fix_command="echo fix",
            max_attempts=2,
        )
        results = run_verification_loop(cfg)
        # No PASS stage should appear — final result should not be a PASS
        pass_stages = [r for r in results if r.stage == VerifyStage.PASS]
        assert len(pass_stages) == 0
        # The last verify attempt should be a failure
        verify_results = [r for r in results if r.stage == VerifyStage.VERIFY]
        assert verify_results[-1].passed is False


# ---------------------------------------------------------------------------
# run_verification_loop — spec_review
# ---------------------------------------------------------------------------

class TestVerifyLoopSpecReview:
    def test_spec_review_pass(self) -> None:
        cfg = VerifyConfig(
            verify_command="echo ok",
            spec_review_command="echo spec ok",
        )
        results = run_verification_loop(cfg)
        stages = [r.stage for r in results]
        assert stages[0] == VerifyStage.SPEC_REVIEW
        assert results[0].passed is True
        # Verify should also pass
        assert stages[1] == VerifyStage.PASS

    def test_spec_review_fail_stops(self) -> None:
        cfg = VerifyConfig(
            verify_command="echo ok",
            spec_review_command="exit 1",
        )
        results = run_verification_loop(cfg)
        assert len(results) == 1
        assert results[0].stage == VerifyStage.SPEC_REVIEW
        assert results[0].passed is False


# ---------------------------------------------------------------------------
# summarize_verify_results
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_correct_counts(self) -> None:
        results = [
            VerifyResult(stage=VerifyStage.SPEC_REVIEW, passed=True, evidence="", attempt=1),
            VerifyResult(stage=VerifyStage.VERIFY, passed=False, evidence="", attempt=1),
            VerifyResult(stage=VerifyStage.FIX, passed=True, evidence="", attempt=1, fix_applied=True),
            VerifyResult(stage=VerifyStage.PASS, passed=True, evidence="", attempt=2),
        ]
        summary = summarize_verify_results(results)
        assert summary["total_attempts"] == 2  # VERIFY + PASS
        assert summary["final_passed"] is True
        assert summary["fix_count"] == 1
        assert "SPEC_REVIEW" in summary["stages_run"]
        assert "VERIFY" in summary["stages_run"]
        assert "FIX" in summary["stages_run"]
        assert "PASS" in summary["stages_run"]

    def test_empty_results(self) -> None:
        summary = summarize_verify_results([])
        assert summary["total_attempts"] == 0
        assert summary["final_passed"] is False


# ---------------------------------------------------------------------------
# format_verify_report
# ---------------------------------------------------------------------------

class TestFormatReport:
    def test_contains_expected_strings(self) -> None:
        results = [
            VerifyResult(stage=VerifyStage.PASS, passed=True, evidence="all good", attempt=1),
        ]
        report = format_verify_report(results)
        assert "Verification Report" in report
        assert "PASS" in report
        assert "all good" in report
        assert "Total attempts: 1" in report
        assert "Final passed: True" in report

    def test_empty_results(self) -> None:
        report = format_verify_report([])
        assert "No verification results" in report
