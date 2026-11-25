# HF WhatsApp Status Publisher - Verificador de atualizacoes
# Uso: VerificarAtualizacao.ps1 [-Silent]
# Obs.: texto sem acentos de proposito (PowerShell 5.1 le o arquivo como ANSI).

param([switch]$Silent)

$ErrorActionPreference = 'Stop'

$BaseUrl = 'https://github.com/hfsoftwaree/HF_WhatsApp_Status_Publish/releases/download/installer'
$Dir = $PSScriptRoot

# Arquivos que podem estar em execucao durante a atualizacao: ficam como .novo
# e o Start.bat os aplica na proxima abertura.
$Staged = @('Start.bat')

# Arquivo cuja opcao START_MINIMIZED escolhida pelo cliente deve ser preservada.
$PreserveFile = 'HF_WhatsApp_Status_Publisher.py'
$MinPattern = '(?m)^START_MINIMIZED\s*=\s*(True|False)'

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Say($msg) { if (-not $Silent) { Write-Host $msg } }

function Get-Sha([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '')
}

# Hash do arquivo local. No .py, ignora a escolha do cliente em START_MINIMIZED
# (compara como se fosse False, que e o valor padrao publicado no Release).
function Get-LocalHash([string]$path, [string]$name) {
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    $bytes = [IO.File]::ReadAllBytes($path)
    if ($name -eq $PreserveFile) {
        $text = [Text.Encoding]::UTF8.GetString($bytes)
        $text = [regex]::Replace($text, $MinPattern, 'START_MINIMIZED = False')
        $bytes = [Text.Encoding]::UTF8.GetBytes($text)
    }
    Get-Sha $bytes
}

# 1. Baixa o manifesto (sem internet: sai em silencio para nao atrapalhar o Start)
try {
    $raw = (Invoke-WebRequest -Uri "$BaseUrl/manifest.json" -UseBasicParsing -TimeoutSec 15).Content
    if ($raw -is [byte[]]) { $raw = [Text.Encoding]::UTF8.GetString($raw) }
    $manifest = ($raw.TrimStart([char]0xFEFF)) | ConvertFrom-Json
} catch {
    Say 'Nao foi possivel verificar atualizacoes (sem conexao ou Release indisponivel).'
    exit 0
}

# 2. Descobre o que mudou
$pending = @()
foreach ($item in $manifest.arquivos.PSObject.Properties) {
    $name = $item.Name
    $expected = $item.Value.ToString().ToLower()
    $local = Get-LocalHash (Join-Path $Dir $name) $name
    if ($local -ne $expected) { $pending += $name }
}

if ($pending.Count -eq 0) {
    Say "Programa atualizado (versao $($manifest.versao))."
    exit 0
}

Say "Atualizacao disponivel: versao $($manifest.versao)"
Say ("Arquivos: " + ($pending -join ', '))

# 3. Baixa tudo para uma pasta temporaria e confere os hashes antes de substituir
$tmp = Join-Path $env:TEMP ('hfupd_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null

try {
    foreach ($name in $pending) {
        $dest = Join-Path $tmp $name
        Invoke-WebRequest -Uri "$BaseUrl/$name" -OutFile $dest -UseBasicParsing -TimeoutSec 120
        $got = Get-Sha ([IO.File]::ReadAllBytes($dest))
        $want = $manifest.arquivos.$name.ToString().ToLower()
        if ($got -ne $want) {
            throw "Hash invalido para $name (download corrompido ou Release incompleto)."
        }
    }
} catch {
    Say "Atualizacao cancelada, nada foi alterado: $($_.Exception.Message)"
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    exit 1
}

# 4. Backup e substituicao
$backup = Join-Path $Dir ('Backup_Atualizacao\' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null

foreach ($name in $pending) {
    $target = Join-Path $Dir $name
    $new = Join-Path $tmp $name

    try {
        if (Test-Path -LiteralPath $target) {
            Copy-Item -LiteralPath $target -Destination (Join-Path $backup $name) -Force
        }

        # Preserva a opcao START_MINIMIZED escolhida pelo cliente
        if ($name -eq $PreserveFile -and (Test-Path -LiteralPath $target)) {
            $oldText = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($target))
            $m = [regex]::Match($oldText, $MinPattern)
            if ($m.Success) {
                $newText = [Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($new))
                $newText = [regex]::Replace($newText, $MinPattern, "START_MINIMIZED = $($m.Groups[1].Value)")
                [IO.File]::WriteAllBytes($new, [Text.Encoding]::UTF8.GetBytes($newText))
            }
        }

        if (($Staged -contains $name) -and (Test-Path -LiteralPath $target)) {
            Copy-Item -LiteralPath $new -Destination "$target.novo" -Force
            Say "  $name -> sera aplicado na proxima abertura"
        } else {
            Copy-Item -LiteralPath $new -Destination $target -Force
            Say "  $name -> atualizado"
        }
    } catch {
        Say "  Falha ao atualizar $name : $($_.Exception.Message)"
    }
}

Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
Say "Atualizacao concluida (versao $($manifest.versao))."
exit 0
