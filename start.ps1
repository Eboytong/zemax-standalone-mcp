param([ValidateSet('full','compact')][string]$ToolMode)
$ErrorActionPreference = 'Stop'
$VenvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) { throw 'Run install.ps1 first.' }
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
if (-not $env:ZEMAX_OUTPUT_DIR) { $env:ZEMAX_OUTPUT_DIR = Join-Path $PSScriptRoot '.local\runs' }
if (-not $env:ZEMAX_STATE_DIR) { $env:ZEMAX_STATE_DIR = Join-Path $PSScriptRoot '.local\state' }
if ($ToolMode) { $env:ZEMAX_TOOL_MODE = $ToolMode }
& $VenvPython -B -m zemax_mcp
exit $LASTEXITCODE
