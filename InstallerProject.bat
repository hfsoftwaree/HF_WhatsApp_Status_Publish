
@echo off
setlocal EnableExtensions

title HF WhatsApp Status Publisher - Instalacao

set "DEST=C:\HF_WhatsApp"
set "BASE=https://github.com/hfsoftwaree/HF_WhatsApp_Status_Publish/releases/download/installer"
set "PYTHON_FILE=%TEMP%\HF_Python_Path.txt"

echo ==================================================
echo       HF WHATSAPP STATUS PUBLISHER
echo       Instalador automatico
echo ==================================================
echo.
echo Pasta de instalacao: %DEST%
echo.

:: --------------------------------------------------
:: 1. CRIAR PASTA
:: --------------------------------------------------

echo [1/10] Preparando pasta de instalacao...

if not exist "%DEST%" mkdir "%DEST%"

if not exist "%DEST%" (
    echo ERRO: nao foi possivel criar a pasta.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 2. BAIXAR ATUALIZADOR
:: --------------------------------------------------

echo.
echo [2/10] Baixando o atualizador...

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%BASE%/VerificarAtualizacao.ps1' -OutFile '%DEST%\VerificarAtualizacao.ps1' -UseBasicParsing -TimeoutSec 60; Invoke-WebRequest -Uri '%BASE%/VerificarAtualizacao.bat' -OutFile '%DEST%\VerificarAtualizacao.bat' -UseBasicParsing -TimeoutSec 60 } catch { Write-Host $_.Exception.Message; exit 1 }"

if errorlevel 1 (
    echo ERRO ao baixar o atualizador.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 3. BAIXAR ARQUIVOS DO PROGRAMA
:: --------------------------------------------------

echo.
echo [3/10] Baixando os arquivos do programa...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\VerificarAtualizacao.ps1"

if errorlevel 1 (
    echo ERRO ao executar o atualizador.
    pause
    exit /b 1
)

if not exist "%DEST%\Start.bat" (
    echo ERRO: arquivo Start.bat nao encontrado.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 4  CRIAR ESTRUTURA DE PASTAS
:: --------------------------------------------------

echo.
echo [4/10] Criando estrutura de pastas...
echo.

for %%D in (
    "Config"
    "Status"
    "Publicados"
    "Erros"
    "Perfil_WhatsApp"
    "Logs"
) do (
    if not exist "%DEST%\%%~D" (
        mkdir "%DEST%\%%~D"
        echo Criada: %%~D
    ) else (
        echo Existente: %%~D
    )
)

:: Criar config.json somente se ainda nao existir
if not exist "%DEST%\Config\config.json" (
    (
        echo {
        echo     "agendamento_ativo": true,
        echo     "horario_envio": "08:00"
        echo }
    ) > "%DEST%\Config\config.json"

    echo Arquivo config.json criado.
) else (
    echo Configuracao existente preservada.
)


:: --------------------------------------------------
:: 5. BAIXAR E INSTALAR A ULTIMA VERSAO ESTAVEL
:: --------------------------------------------------

echo.
echo [5/10] Baixando e instalando Python...
echo.
echo Consultando versoes estaveis oficiais...
echo.

set "PYTHON_FILE=%TEMP%\HF_Python_Path.txt"

if exist "%PYTHON_FILE%" del "%PYTHON_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $index = Invoke-RestMethod -Uri 'https://api.nuget.org/v3-flatcontainer/python/index.json' -TimeoutSec 60; $stable = @($index.versions | Where-Object { $_ -match '^\d+\.\d+\.\d+$' } | ForEach-Object { [version]$_ } | Sort-Object -Descending); if ($stable.Count -eq 0) { throw 'Nenhuma versao estavel encontrada.' }; $v = $stable[0]; $ver = $v.ToString(); Write-Host ('Ultima versao estavel: Python ' + $ver); $arch = $env:PROCESSOR_ARCHITECTURE; if ($env:PROCESSOR_ARCHITEW6432) { $arch = $env:PROCESSOR_ARCHITEW6432 }; switch ($arch.ToUpperInvariant()) { 'AMD64' { $suffix = 'amd64' } 'ARM64' { $suffix = 'arm64' } 'X86' { $suffix = '' } default { throw 'Arquitetura nao suportada: ' + $arch } }; if ($suffix) { $file = 'python-' + $ver + '-' + $suffix + '.exe' } else { $file = 'python-' + $ver + '.exe' }; $url = 'https://www.python.org/ftp/python/' + $ver + '/' + $file; $installer = Join-Path $env:TEMP $file; Write-Host ''; Write-Host 'Baixando instalador oficial...'; Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing -TimeoutSec 300; if ((Get-Item $installer).Length -lt 5000000) { throw 'Arquivo de instalacao incompleto.' }; Write-Host ''; Write-Host 'Instalando Python silenciosamente...'; $args = @('/quiet','InstallAllUsers=0','PrependPath=1','Include_pip=1','Include_launcher=0','Include_test=0','Include_doc=0'); $p = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru; if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) { throw ('Erro no instalador. Codigo: ' + $p.ExitCode) }; $python = Join-Path $env:LOCALAPPDATA ('Programs\Python\Python' + $v.Major + $v.Minor + '\python.exe'); if (!(Test-Path $python)) { throw 'Python nao encontrado apos a instalacao.' }; Set-Content -Path '%PYTHON_FILE%' -Value $python -Encoding ASCII; Write-Host ''; Write-Host 'Python instalado com sucesso:'; & $python --version; if ($LASTEXITCODE -ne 0) { throw 'Falha ao executar Python.' }; exit 0 } catch { Write-Host ''; Write-Host ('ERRO: ' + $_.Exception.Message); exit 1 }"

if errorlevel 1 (
    echo.
    echo ERRO ao instalar Python.
    pause
    exit /b 1
)

if not exist "%PYTHON_FILE%" (
    echo ERRO: caminho do Python nao encontrado.
    pause
    exit /b 1
)

set /p PYTHON_EXE=<"%PYTHON_FILE%"

if not exist "%PYTHON_EXE%" (
    echo ERRO: executavel Python nao encontrado.
    pause
    exit /b 1
)

for %%I in ("%PYTHON_EXE%") do set "PYTHON_DIR=%%~dpI"

set "PATH=%PYTHON_DIR%;%PYTHON_DIR%Scripts;%PATH%"


:: --------------------------------------------------
:: 6. ATUALIZAR PIP
:: --------------------------------------------------

echo.
echo [6/10] Atualizando PIP...

"%PYTHON_EXE%" -m ensurepip --upgrade

if errorlevel 1 (
    echo ERRO ao preparar PIP.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m pip install --upgrade pip

if errorlevel 1 (
    echo ERRO ao atualizar PIP.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 7. INSTALAR PLAYWRIGHT
:: --------------------------------------------------

echo.
echo [7/10] Instalando Playwright...

"%PYTHON_EXE%" -m pip install --upgrade playwright

if errorlevel 1 (
    echo ERRO ao instalar Playwright.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 8. INSTALAR CHROMIUM
:: --------------------------------------------------

echo.
echo [8/10] Instalando Chromium...

"%PYTHON_EXE%" -m playwright install chromium

if errorlevel 1 (
    echo ERRO ao instalar Chromium.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: 9. VERIFICACAO FINAL
:: --------------------------------------------------

echo.
echo [9/10] Verificando ambiente...
echo.

echo Python:
"%PYTHON_EXE%" --version

if errorlevel 1 goto ERRO_FINAL

echo.
echo PIP:
"%PYTHON_EXE%" -m pip --version

if errorlevel 1 goto ERRO_FINAL

echo.
echo Playwright:
"%PYTHON_EXE%" -m playwright --version

if errorlevel 1 goto ERRO_FINAL

echo.
echo Chromium:
"%PYTHON_EXE%" -m playwright install --list

if errorlevel 1 goto ERRO_FINAL

:: --------------------------------------------------
:: 10. CRIAR ATALHO
:: --------------------------------------------------

echo.
choice /c SN /n /m "Criar um atalho na area de trabalho? (S/N): "

if errorlevel 2 goto FIM

powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\HF WhatsApp Status.lnk'); $s.TargetPath = '%DEST%\Start.bat'; $s.WorkingDirectory = '%DEST%'; $s.Save()"

echo.
echo Atalho criado.

goto FIM

:: --------------------------------------------------
:: ERRO FINAL
:: --------------------------------------------------

:ERRO_FINAL

echo.
echo ERRO NA VERIFICACAO DO AMBIENTE.
echo Verifique as mensagens anteriores.
echo.
pause
exit /b 1

:: --------------------------------------------------
:: CONCLUSAO
:: --------------------------------------------------

:FIM

echo.
echo ==================================================
echo          INSTALACAO CONCLUIDA!
echo ==================================================
echo.
echo Ambiente preparado para HF WhatsApp Status Publisher.
echo.
echo Proximos passos:
echo.
echo 1. Configure o horario de execucao em:
echo    %DEST%\Config
echo.
echo 2. Coloque imagens e videos em:
echo    %DEST%\Status
echo.
echo 3. Execute Start.bat e escaneie o QR Code.
echo.
pause
exit /b 0
