param([string]$PythonExe = 'python')
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
& $PythonExe -B (Join-Path $PSScriptRoot 'build_windows.py')
if ($LASTEXITCODE -ne 0) { throw 'Windows distribution build failed.' }
