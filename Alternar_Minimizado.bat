@echo off
setlocal EnableExtensions

title Alternar modo minimizado - HF WhatsApp Status Publisher

cd /d "%~dp0"

echo ==================================================
echo       HF WHATSAPP STATUS PUBLISHER
echo       Alternar modo minimizado
echo ==================================================
echo.

if not exist "HF_WhatsApp_Status_Publisher.py" (
    echo ERRO: HF_WhatsApp_Status_Publisher.py nao encontrado.
    echo Coloque este arquivo na mesma pasta do programa.
    echo.
    pause
    exit /b 1
)

:: Inverte START_MINIMIZED entre True e False no script.
:: Codigos de saida: 10 = agora False | 11 = agora True | 2 = linha nao encontrada

powershell -NoProfile -ExecutionPolicy Bypass -Command "$f=(Resolve-Path 'HF_WhatsApp_Status_Publisher.py').Path; $t=[IO.File]::ReadAllText($f,[Text.Encoding]::UTF8); $m=[regex]::Match($t,'(?m)^START_MINIMIZED = (True|False)'); if(-not $m.Success){exit 2}; $g=$m.Groups[1]; if($g.Value -eq 'True'){$n='False';$c=10}else{$n='True';$c=11}; $t=$t.Remove($g.Index,$g.Length).Insert($g.Index,$n); [IO.File]::WriteAllText($f,$t,(New-Object Text.UTF8Encoding $false)); exit $c"

if %errorlevel%==10 goto DESLIGADO
if %errorlevel%==11 goto LIGADO

echo.
echo ERRO: nao foi possivel alterar a opcao START_MINIMIZED.
echo Abra HF_WhatsApp_Status_Publisher.py e altere manualmente.
echo.
pause
exit /b 1

:LIGADO
echo.
echo Modo minimizado: ATIVADO
echo O navegador abrira minimizado na proxima execucao.
echo.
echo Observacao: na primeira execucao (QR Code), mantenha DESATIVADO.
goto FIM

:DESLIGADO
echo.
echo Modo minimizado: DESATIVADO
echo O navegador abrira visivel na proxima execucao.

:FIM
echo.
echo Execute este arquivo novamente para alternar.
echo.
pause
endlocal
