from pathlib import Path

from scripts import policy_scan


def test_scan_paths_reports_policy_smells(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        "We also write to legacy output for now.\n"
        "If missing, use legacy behavior.\n"
        "This compat path remains.\n",
        encoding="utf-8",
    )

    findings = policy_scan.scan_paths(tmp_path)

    assert {item["code"] for item in findings} == {"dual_write", "silent_fallback", "shadow_path"}


def test_main_warning_mode_is_non_blocking(tmp_path: Path, capsys) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("# fallback to legacy path\n", encoding="utf-8")

    rc = policy_scan.main([str(tmp_path)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "policy-scan:" in out
    assert "WARN" in out


def test_main_strict_mode_blocks_on_findings(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text("# dual-write to legacy\n", encoding="utf-8")

    rc = policy_scan.main([str(tmp_path), "--strict"])

    assert rc == 1


def test_scan_paths_skips_policy_prompt_skill_and_test_dirs(tmp_path: Path) -> None:
    (tmp_path / "policy").mkdir()
    (tmp_path / "prompts").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "scripts").mkdir()

    (tmp_path / "policy" / "rules.md").write_text("dual-write to legacy\n", encoding="utf-8")
    (tmp_path / "prompts" / "worker.md").write_text("fallback to legacy\n", encoding="utf-8")
    (tmp_path / "skills" / "review.md").write_text("shadow path\n", encoding="utf-8")
    (tmp_path / "tests" / "test_scan.py").write_text("compat path\n", encoding="utf-8")
    (tmp_path / "scripts" / "policy_scan.py").write_text("mirror to legacy\n", encoding="utf-8")

    findings = policy_scan.scan_paths(tmp_path)

    assert findings == []


def test_scan_paths_skips_nested_excluded_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "packages" / "foo" / "tests"
    nested.mkdir(parents=True)
    (nested / "fixture.py").write_text("fallback to legacy\n", encoding="utf-8")

    findings = policy_scan.scan_paths(tmp_path)

    assert findings == []


def test_scan_paths_ignores_markdown_docs(tmp_path: Path) -> None:
    doc = tmp_path / "README.md"
    doc.write_text("compat path\nfallback to legacy\n", encoding="utf-8")

    findings = policy_scan.scan_paths(tmp_path)

    assert findings == []
