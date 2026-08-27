[CmdletBinding()]
param([switch]$ValidateOnly)

$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $PSScriptRoot
$InstallDir = Join-Path $env:LOCALAPPDATA 'Programs\JARVIS'
$DataDir = Join-Path $env:LOCALAPPDATA 'JARVIS'
$Executable = Join-Path $InstallDir 'JARVIS.exe'
$DebugExecutable = Join-Path $InstallDir 'JARVIS-Debug.exe'

function Ask([string]$Message, [bool]$Default = $false) {
    $suffix = if ($Default) { '[S/n]' } else { '[s/N]' }
    $answer = Read-Host "$Message $suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $Default }
    return $answer.Trim().ToLowerInvariant().StartsWith('s')
}

Write-Host ''
Write-Host 'J.A.R.V.I.S. 1.0.0 - Instalador' -ForegroundColor Cyan
Write-Host '=================================' -ForegroundColor DarkCyan

if ($env:OS -ne 'Windows_NT') { throw 'Este pacote requer Windows.' }
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Este pacote requer Windows x64.' }
if (-not (Test-Path (Join-Path $PackageRoot 'JARVIS.exe'))) { throw 'JARVIS.exe nao foi encontrado no pacote extraido.' }
Write-Host '[OK] Windows x64 e pacote verificados.' -ForegroundColor Green

if ($ValidateOnly) {
    Write-Host '[OK] Scripts e estrutura do instalador validados.' -ForegroundColor Green
    exit 0
}

New-Item -ItemType Directory -Force -Path $InstallDir, $DataDir | Out-Null
Get-ChildItem -LiteralPath $PackageRoot -Force | Where-Object {
    $_.Name -notin @('install.bat', 'portable.flag')
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $InstallDir -Recurse -Force
}
Write-Host "[OK] Aplicacao instalada em $InstallDir" -ForegroundColor Green

& $DebugExecutable --prepare
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar configuracoes e banco de dados.' }
Write-Host "[OK] Dados pessoais serao mantidos em $DataDir" -ForegroundColor Green

$Ollama = Get-Command ollama.exe -ErrorAction SilentlyContinue
$OllamaExecutable = if ($Ollama) { $Ollama.Source } else { $null }
if (-not $Ollama) {
    $OllamaPath = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (Test-Path $OllamaPath) {
        $Ollama = Get-Item $OllamaPath
        $OllamaExecutable = $Ollama.FullName
    }
}
if ($Ollama) {
    Write-Host '[OK] Ollama detectado.' -ForegroundColor Green
    if (Ask 'Baixar/verificar o modelo qwen3:4b agora? Download aproximado: 2,5 GB.') {
        & $OllamaExecutable pull qwen3:4b
    }
} else {
    Write-Host ''
    Write-Host 'O J.A.R.V.I.S. utiliza Ollama para inteligencia artificial local.' -ForegroundColor Yellow
    Write-Host 'Os comandos diretos funcionam sem ele. Para conversas e planejamento, instale:'
    Write-Host 'https://ollama.com/download/windows' -ForegroundColor Cyan
    Write-Host 'Depois execute: ollama pull qwen3:4b'
}

Write-Host '[OK] Voz do Windows (SAPI) disponivel como TTS padrao.' -ForegroundColor Green
Write-Host '[INFO] Piper e opcional e pode ser configurado nas preferencias.'
Write-Host '[OK] Modelo ONNX da wake word Jarvis incluido.' -ForegroundColor Green

if (Ask 'Preparar o modelo faster-whisper small agora? Download aproximado: 500 MB.') {
    $env:HF_HOME = Join-Path $DataDir 'cache\huggingface'
    & $DebugExecutable --download-stt small
    if ($LASTEXITCODE -ne 0) { Write-Warning 'O modelo STT nao foi baixado. Tente novamente pelo modo debug.' }
} else {
    Write-Host '[INFO] O modelo STT sera obtido quando voce decidir ativar a voz.'
}

Write-Host ''
Write-Host 'Executando diagnostico de dependencias e microfone...'
& $DebugExecutable --diagnostics

$Shell = New-Object -ComObject WScript.Shell
if (Ask 'Criar atalho J.A.R.V.I.S. na area de trabalho?' $true) {
    $Shortcut = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'J.A.R.V.I.S..lnk'))
    $Shortcut.TargetPath = $Executable
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.IconLocation = "$Executable,0"
    $Shortcut.Save()
    Write-Host '[OK] Atalho criado.' -ForegroundColor Green
}

if (Ask 'Iniciar J.A.R.V.I.S. junto com o Windows?') {
    $Startup = [Environment]::GetFolderPath('Startup')
    $Shortcut = $Shell.CreateShortcut((Join-Path $Startup 'J.A.R.V.I.S..lnk'))
    $Shortcut.TargetPath = $Executable
    $Shortcut.Arguments = '--background'
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.IconLocation = "$Executable,0"
    $Shortcut.Save()
    Write-Host '[OK] Inicializacao com Windows ativada.' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Instalacao concluida. Na primeira abertura, o assistente de configuracao sera exibido.' -ForegroundColor Green
if (Ask 'Abrir J.A.R.V.I.S. agora?' $true) { Start-Process -FilePath $Executable -WorkingDirectory $InstallDir }
