@echo off
title HF WhatsApp Status Publisher

cd /d "%~dp0"

rem Aplica uma nova versao deste proprio arquivo, baixada na execucao anterior
if exist "Start.bat.novo" (move /y "Start.bat.novo" "Start.bat" >nul & start "" "%~dp0Start.bat" & exit)

rem Verifica atualizacoes (silencioso; sem internet, segue normalmente)
call VerificarAtualizacao.bat -Silent

where py >nul 2>nul
if %errorlevel%==0 (
    py "HF_WhatsApp_Status_Publisher.py"
) else (
    python "HF_WhatsApp_Status_Publisher.py"
)