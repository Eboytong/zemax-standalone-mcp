$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$runtime = Join-Path $repoRoot '.local\v1.4.1-2026r1'
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
foreach ($name in @('compat_plugin.py', 'run_all.py', 'report.py', 'status.py', 'tool-names.json')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $runtime $name)
}
if (-not (Test-Path -LiteralPath (Join-Path $runtime 'retry-plan.json'))) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'retry-plan.json') -Destination (Join-Path $runtime 'retry-plan.json')
}
$env:PYTHONPATH = "$runtime;$(Join-Path $repoRoot 'src');$repoRoot"
$env:ZEMAX_INSTALL_DIR = 'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio'
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location $repoRoot
try {
    & $pythonExe -X utf8 -B -m pytest tests --collect-only -q -p no:cacheprovider -p compat_plugin *> (Join-Path $runtime 'collection.log')
    if ($LASTEXITCODE -ne 0) { throw 'Test collection failed. See collection.log.' }
    & $pythonExe -X utf8 -B -m pytest tests --ignore=tests/native -q -p no:cacheprovider --junitxml (Join-Path $runtime 'unit.xml') *> (Join-Path $runtime 'unit.log')
    $ordinaryExit = $LASTEXITCODE
    & $pythonExe -X utf8 -B (Join-Path $runtime 'run_all.py') *> (Join-Path $runtime 'runner.log')
    if ($LASTEXITCODE -ne 0) { throw 'Native runner failed. See runner.log.' }
    & $pythonExe -X utf8 -B (Join-Path $runtime 'report.py')
    if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
    $result = Get-Content -LiteralPath (Join-Path $runtime 'summary.json') -Raw | ConvertFrom-Json
    if ($ordinaryExit -ne 0 -or $result.native.failed -gt 0 -or $result.native.not_completed -gt 0) { exit 1 }
} finally {
    Pop-Location
}
