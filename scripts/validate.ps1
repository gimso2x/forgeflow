$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $Root
try {
    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        & ".\scripts\setup.ps1"
    }
    & ".\.venv\Scripts\python.exe" scripts/check_environment.py
    & ".\.venv\Scripts\python.exe" scripts/check_plugin_versions.py
    & ".\.venv\Scripts\python.exe" scripts/validate_context_paths.py
    & ".\.venv\Scripts\python.exe" scripts/validate_structure.py
    & ".\.venv\Scripts\python.exe" scripts/validate_policy.py
    & ".\.venv\Scripts\python.exe" scripts/validate_generated.py
    & ".\.venv\Scripts\python.exe" scripts/validate_sample_artifacts.py
    & ".\.venv\Scripts\python.exe" scripts/run_adherence_evals.py
    & ".\.venv\Scripts\python.exe" -m pytest tests/runtime -q
    & ".\.venv\Scripts\python.exe" -m pytest tests/test_first_clone_setup.py -q
    & ".\.venv\Scripts\python.exe" -m pytest tests/test_agent_preset_install.py -q
    & ".\.venv\Scripts\python.exe" -m pytest tests/test_codex_plugin_install.py -q
    & ".\.venv\Scripts\python.exe" -m pytest tests/test_plugin_manifests.py -q
}
finally {
    Pop-Location
}
