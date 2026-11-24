
@echo off
setlocal EnableExtensions

title Instalacao - HF WhatsApp Status Publisher

cd /d "%~dp0"

echo ==================================================
echo       HF WHATSAPP STATUS PUBLISHER
echo       Instalador automatico
echo ==================================================
echo.

:: --------------------------------------------------
:: 1. VERIFICAR WINGET
:: --------------------------------------------------

echo [1/6] Verificando Windows Package Manager...

where winget >nul 2>&1

if errorlevel 1 (
    echo.
    echo ERRO: WinGet nao encontrado.
    echo Atualize o App Installer pela Microsoft Store.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 2. INSTALAR PYTHON INSTALL MANAGER
:: --------------------------------------------------

echo.
echo [2/6] Verificando Python Install Manager...

where pymanager >nul 2>&1

if errorlevel 1 (
    echo.
    echo Instalando Python Install Manager oficial...
    echo.

    winget install --id 9NQ7512CXL7T -e --silent --accept-package-agreements --accept-source-agreements --disable-interactivity

    if errorlevel 1 (
        echo.
        echo ERRO ao instalar Python Install Manager.
        pause
        exit /b 1
    )
)

:: Atualizar PATH da sessao

set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WindowsApps"
set "PATH=%PATH%;%LOCALAPPDATA%\Python\bin"

:: Aguardar disponibilizacao do gerenciador

set "TENTATIVAS=0"

:AGUARDAR_MANAGER

where pymanager >nul 2>&1

if not errorlevel 1 goto MANAGER_OK

set /a TENTATIVAS+=1

if %TENTATIVAS% GEQ 15 (
    echo.
    echo ERRO: Python Install Manager nao foi localizado.
    echo Reinicie o Windows e tente novamente.
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul
goto AGUARDAR_MANAGER

:MANAGER_OK

:: --------------------------------------------------
:: 3. CONFIGURAR PYTHON INSTALL MANAGER
:: --------------------------------------------------

echo.
echo [3/6] Configurando Python Install Manager...

pymanager install --configure -y

if errorlevel 1 (
    echo.
    echo ERRO na configuracao do gerenciador.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 4. INSTALAR PYTHON ESTAVEL MAIS RECENTE
:: --------------------------------------------------

echo.
echo [4/6] Instalando Python estavel mais recente...

pymanager install --update default

if errorlevel 1 (
    echo.
    echo ERRO ao instalar ou atualizar Python.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 5. INSTALAR PLAYWRIGHT
:: --------------------------------------------------

echo.
echo [5/6] Instalando Playwright...

pymanager exec -m pip install --upgrade pip

if errorlevel 1 (
    echo.
    echo ERRO ao atualizar PIP.
    pause
    exit /b 1
)

pymanager exec -m pip install --upgrade playwright

if errorlevel 1 (
    echo.
    echo ERRO ao instalar Playwright.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 6. INSTALAR CHROMIUM
:: --------------------------------------------------

echo.
echo [6/6] Instalando Chromium...

pymanager exec -m playwright install chromium

if errorlevel 1 (
    echo.
    echo ERRO ao instalar Chromium.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: VERIFICACAO FINAL
:: --------------------------------------------------

echo.
echo ==================================================
echo          VERIFICACAO DA INSTALACAO
echo ==================================================

echo.
echo Python:
pymanager exec --version

echo.
echo Playwright:
pymanager exec -m playwright --version

echo.
echo ==================================================
echo          INSTALACAO CONCLUIDA!
echo ==================================================
echo.
echo Ambiente preparado para HF WhatsApp Status Publisher.
echo.
pause
exit /b 0
