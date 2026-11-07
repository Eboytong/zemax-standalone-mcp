param(
    [string]$PythonExe = 'python',
    [switch]$WithReports,
    [switch]$WithGeometry
)
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
& $PythonExe -c "import sys,struct; assert sys.version_info[:2] == (3,14), 'Python 3.14 required'; assert struct.calcsize('P') == 8, 'x64 Python required'"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 x64 is required.' }
$Wheel = Get-Item -LiteralPath (Join-Path $PackageRoot 'releases\0.1.61\zemax_standalone_mcp-0.1.61-py3-none-any.whl')
$EnvRoot = Join-Path $PackageRoot '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $EnvRoot 'Scripts\python.exe'))) {
    & $PythonExe -m venv $EnvRoot
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create Python environment.' }
}
$VenvPython = Join-Path $EnvRoot 'Scripts\python.exe'
& $VenvPython -c "import sys,struct; assert sys.version_info[:2] == (3,14) and struct.calcsize('P') == 8"
if ($LASTEXITCODE -ne 0) { throw 'Existing environment must use Python 3.14 x64.' }
$Extras = @()
if ($WithReports) { $Extras += 'reports' }
if ($WithGeometry) { $Extras += 'geometry' }
$Requirement = $Wheel.FullName
if ($Extras.Count -gt 0) { $Requirement += '[' + ($Extras -join ',') + ']' }
& $VenvPython -m pip install --constraint (Join-Path $PackageRoot 'requirements\all.lock.txt') $Requirement
if ($LASTEXITCODE -ne 0) { throw 'Failed to install MCP dependencies.' }
$OutputRoot = Join-Path $PackageRoot '.local\runs'
$StateRoot = Join-Path $PackageRoot '.local\state'
$ConfigRoot = Join-Path $PackageRoot '.local\config'
New-Item -ItemType Directory -Path $ConfigRoot -Force | Out-Null
$ConfigPath = Join-Path $ConfigRoot 'mcp.config.json'
$ServerConfig = @{
    command = $VenvPython
    args = @('-B', '-m', 'zemax_mcp')
    cwd = $PackageRoot
    env = @{
        ZEMAX_INSTALL_DIR = 'C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio'
        ZEMAX_OUTPUT_DIR = $OutputRoot
        ZEMAX_STATE_DIR = $StateRoot
        PYTHONUTF8 = '1'
        PYTHONDONTWRITEBYTECODE = '1'
    }
}
@{ mcpServers = @{ zemax = $ServerConfig } } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
Write-Host "Installed. Client configuration: $ConfigPath"
