param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OrchestratorArgs
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $Root
try {
    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        & ".\scripts\setup.ps1"
    }
    & ".\.venv\Scripts\python.exe" scripts/run_orchestrator.py @OrchestratorArgs
}
finally {
    Pop-Location
}
