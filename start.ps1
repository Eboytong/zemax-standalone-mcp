$ErrorActionPreference = 'Stop'
$VenvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) { throw 'Run install.ps1 first.' }
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
if (-not $env:ZEMAX_OUTPUT_DIR) { $env:ZEMAX_OUTPUT_DIR = Join-Path $PSScriptRoot 'outputs\runs' }
if (-not $env:ZEMAX_STATE_DIR) { $env:ZEMAX_STATE_DIR = Join-Path $PSScriptRoot 'outputs\state' }
& $VenvPython -B -m zemax_mcp
exit $LASTEXITCODE
