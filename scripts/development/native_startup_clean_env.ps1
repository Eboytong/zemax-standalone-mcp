param(
    [string]$BasePython = 'C:\Users\tonge\anaconda3\python.exe',
    [string]$RuntimeRoot = (Join-Path $env:USERPROFILE 'Zemax_MCP_Runtime\.venv')
)
$ErrorActionPreference = 'Stop'
& $BasePython -B -X utf8 (Join-Path $PSScriptRoot 'native_startup_clean_env.py') --runtime-root $RuntimeRoot
exit $LASTEXITCODE
