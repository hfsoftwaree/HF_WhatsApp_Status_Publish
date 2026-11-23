@echo off
title Instalacao - HF WhatsApp Status Publisher

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado.
    echo Instale o Python em https://www.python.org/downloads/
    echo e marque a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

echo Instalando dependencias...
python -m pip install -r requirements.txt

echo Instalando o navegador Chromium...
python -m playwright install chromium

echo.
echo Instalacao concluida.
pause