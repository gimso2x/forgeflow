$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $Root
try {
    $PythonArgs = @()
    $Python = if ($env:PYTHON) {
        $env:PYTHON
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        "python"
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonArgs = @("-3")
        "py"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        "python3"
    } else {
        throw "Python was not found on PATH. Install Python 3.11+ or set `$env:PYTHON."
    }
    & $Python @PythonArgs scripts/install_codex_plugin.py @args
}
finally {
    Pop-Location
}
