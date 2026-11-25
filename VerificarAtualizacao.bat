@echo off
cd /d "%~dp0"

if not exist "VerificarAtualizacao.ps1" (
    echo VerificarAtualizacao.ps1 nao encontrado.
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0VerificarAtualizacao.ps1" %*

rem Se executado com duplo clique (sem -Silent), mantem a janela aberta.
echo %* | find /i "-Silent" >nul
if errorlevel 1 pause

exit /b 0
