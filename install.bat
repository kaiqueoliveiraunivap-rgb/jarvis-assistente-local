@echo off
setlocal EnableExtensions
pushd "%~dp0"

echo.
echo  J.A.R.V.I.S. - instalacao local
echo  ==================================

set "JARVIS_PYTHON="
if exist ".venv\Scripts\python.exe" set "JARVIS_PYTHON=.venv\Scripts\python.exe"
if not defined JARVIS_PYTHON (
    where py >nul 2>nul
    if not errorlevel 1 set "JARVIS_PYTHON=py -3"
)
if not defined JARVIS_PYTHON (
    where python >nul 2>nul
    if not errorlevel 1 set "JARVIS_PYTHON=python"
)
if not defined JARVIS_PYTHON (
    echo [ERRO] Python 3.12 ou superior nao foi encontrado.
    echo Instale em https://www.python.org/downloads/windows/ e marque "Add Python to PATH".
    popd
    exit /b 1
)

%JARVIS_PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
    echo [ERRO] E necessario Python 3.12 ou superior.
    popd
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Criando ambiente virtual...
    %JARVIS_PYTHON% -m venv .venv
    if errorlevel 1 goto :failed
) else (
    echo [1/5] Ambiente virtual existente.
)

set "JARVIS_VENV_PY=.venv\Scripts\python.exe"
echo [2/5] Atualizando instalador de pacotes...
"%JARVIS_VENV_PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :failed

echo [3/7] Instalando interface, automacao e voz local...
"%JARVIS_VENV_PY%" -m pip install -r requirements-voice.txt
if errorlevel 1 goto :failed

echo [4/7] Preparando wake word hey_jarvis...
"%JARVIS_VENV_PY%" -c "from openwakeword.utils import download_models; download_models(['hey_jarvis'])"
if errorlevel 1 (
    echo [AVISO] O modelo dedicado nao foi baixado. O fallback por Whisper continuara disponivel.
)

echo [5/7] Baixando o modelo Whisper small para uso offline...
"%JARVIS_VENV_PY%" -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8'); print('Whisper small pronto.')"
if errorlevel 1 goto :failed

if /I "%~1"=="--with-browser" (
    echo [6/7] Instalando navegador isolado do Playwright...
    "%JARVIS_VENV_PY%" -m pip install -r requirements-browser.txt
    if errorlevel 1 goto :failed
    "%JARVIS_VENV_PY%" -m playwright install chromium
    if errorlevel 1 goto :failed
) else (
    echo [6/7] Playwright opcional nao solicitado.
)

echo [7/7] Preparando banco e executando diagnostico...
"%JARVIS_VENV_PY%" main.py --check
if errorlevel 1 goto :failed
"%JARVIS_VENV_PY%" -m jarvis.diagnostics
if errorlevel 1 goto :failed

where ollama >nul 2>nul
if errorlevel 1 (
    echo.
    echo [AVISO] Ollama nao foi encontrado no PATH.
    echo Instale em https://ollama.com/download/windows e depois execute:
    echo     ollama pull qwen3:4b
) else (
    echo Ollama localizado.
)

echo.
echo Instalacao concluida. Execute start_jarvis.bat
popd
exit /b 0

:failed
echo.
echo [ERRO] A instalacao falhou. Revise a mensagem acima.
popd
exit /b 1
