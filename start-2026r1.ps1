$ErrorActionPreference = 'Stop'
$env:ZEMAX_INSTALL_DIR = 'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio'
$env:ZEMAX_OUTPUT_DIR = Join-Path $PSScriptRoot '.local\runs-2026r1'
$env:ZEMAX_STATE_DIR = Join-Path $PSScriptRoot '.local\state-2026r1'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -B -m zemax_mcp
exit $LASTEXITCODE
