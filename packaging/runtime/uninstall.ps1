[CmdletBinding()]
param([switch]$KeepData)

$ErrorActionPreference = 'Stop'
$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\JARVIS'
$DataDir = Join-Path $env:LOCALAPPDATA 'JARVIS'
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'J.A.R.V.I.S..lnk'
$StartupShortcut = Join-Path ([Environment]::GetFolderPath('Startup')) 'J.A.R.V.I.S..lnk'
$StartupCommand = Join-Path ([Environment]::GetFolderPath('Startup')) 'JARVIS_startup.cmd'

Write-Host 'J.A.R.V.I.S. - Desinstalador' -ForegroundColor Cyan
Get-Process -Name 'JARVIS', 'JARVIS-Debug' -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item -LiteralPath $DesktopShortcut, $StartupShortcut, $StartupCommand -Force -ErrorAction SilentlyContinue

$DeleteData = $false
if (-not $KeepData) {
    $answer = Read-Host 'Deseja tambem apagar suas configuracoes e memorias do J.A.R.V.I.S.? [s/N]'
    $DeleteData = -not [string]::IsNullOrWhiteSpace($answer) -and $answer.Trim().ToLowerInvariant().StartsWith('s')
}

if (Test-Path $InstallDir) { Remove-Item -LiteralPath $InstallDir -Recurse -Force }
if ($DeleteData -and (Test-Path $DataDir)) { Remove-Item -LiteralPath $DataDir -Recurse -Force }

Write-Host 'Aplicacao removida.' -ForegroundColor Green
if (-not $DeleteData) { Write-Host "Configuracoes e memorias preservadas em $DataDir" }
