param([ValidateSet('full','compact')][string]$ToolMode)
$ErrorActionPreference = 'Stop'
if (-not $env:ZEMAX_INSTALL_DIR) { $env:ZEMAX_INSTALL_DIR = 'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio' }
if (-not $env:ZEMAX_OUTPUT_DIR) { $env:ZEMAX_OUTPUT_DIR = Join-Path $PSScriptRoot '.local\runs-2026r1' }
if (-not $env:ZEMAX_STATE_DIR) { $env:ZEMAX_STATE_DIR = Join-Path $PSScriptRoot '.local\state-2026r1' }
if ($ToolMode) { $env:ZEMAX_TOOL_MODE = $ToolMode }
elseif (-not $env:ZEMAX_TOOL_MODE) { $env:ZEMAX_TOOL_MODE = 'compact' }
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$VenvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $VenvPython)) { throw 'Run install.ps1 first.' }
& $VenvPython -B -m zemax_mcp
exit $LASTEXITCODE
