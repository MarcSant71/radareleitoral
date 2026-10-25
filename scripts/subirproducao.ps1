param (
    [Parameter(Mandatory = $false)]
    [string]$ServerIp = "2.29.110.124",

    [Parameter(Mandatory = $false)]
    [switch]$IncludeDatabase = $false
)

$ErrorActionPreference = "Stop"

# Raiz do projeto (um nivel acima da pasta scripts)
$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path
$TempArchive = Join-Path $ProjectDir "deploy_package.tar.gz"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[*] Iniciando empacotamento para Hetzner: $ServerIp" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Lista estrita dos arquivos de producao
$ItemsToInclude = @(
    "Dockerfile",
    "docker-compose.yml",
    "Caddyfile",
    "requirements.txt",
    ".streamlit",
    "web",
    "CHANGELOG.md",
    "index.html",
    "og_preview.png"
)

if ($IncludeDatabase) {
    if (Test-Path "$ProjectDir\db\eleicoes.db") {
        Write-Host "[!] Modo Completo: Incluindo banco SQLite (db\eleicoes.db)..." -ForegroundColor Magenta
        $ItemsToInclude += "db\eleicoes.db"
    } elseif (Test-Path "$ProjectDir\db\eleicoes2026.db") {
        Write-Host "[!] Modo Completo: Incluindo banco SQLite legado (db\eleicoes2026.db)..." -ForegroundColor Magenta
        $ItemsToInclude += "db\eleicoes2026.db"
    }
} else {
    Write-Host "[i] Deploy Rapido: Preservando SQLite existente na VPS (use -IncludeDatabase para atualizar o .db)" -ForegroundColor Cyan
}

if (Test-Path "$ProjectDir\db\eleicoes.parquet") {
    $ItemsToInclude += "db\eleicoes.parquet"
} elseif (Test-Path "$ProjectDir\db\eleicoes2026.parquet") {
    $ItemsToInclude += "db\eleicoes2026.parquet"
}
if (Test-Path "$ProjectDir\db\locais_votacao.parquet") {
    $ItemsToInclude += "db\locais_votacao.parquet"
}
if (Test-Path "$ProjectDir\db\locais_secoes.parquet") {
    $ItemsToInclude += "db\locais_secoes.parquet"
}

# Resolve versao do CHANGELOG.md e commit hash do Git de forma automatica
Write-Host "[*] Resolvendo metadados de versao e commit..." -ForegroundColor Yellow
$GitCommit = try { (git -C "$ProjectDir" rev-parse --short HEAD).Trim() } catch { "prod" }
$Changelog = if (Test-Path "$ProjectDir\CHANGELOG.md") { Get-Content "$ProjectDir\CHANGELOG.md" -Raw } else { "" }
$VersionMatch = [regex]::Match($Changelog, '##\s*\[(\d+\.\d+\.\d+)\]\s*-\s*([0-9-]+)')
if (-not $VersionMatch.Success) {
    throw "Erro critico: Nao foi possivel extrair a versao SemVer do CHANGELOG.md"
}
$AppVersion = $VersionMatch.Groups[1].Value
$AppDate = $VersionMatch.Groups[2].Value

$BuildInfo = @{
    versao = $AppVersion
    commit = $GitCommit
    data = $AppDate
} | ConvertTo-Json

# Grava version.json em UTF-8 SEM BOM para compatibilidade com Python em Linux
[System.IO.File]::WriteAllText("$ProjectDir\web\version.json", $BuildInfo, [System.Text.UTF8Encoding]::new($false))
Write-Host "[+] Versao resolvida para o build: v$AppVersion ($GitCommit)" -ForegroundColor Green

Write-Host "[*] Compactando arquivos essenciais..." -ForegroundColor Yellow
Push-Location $ProjectDir
try {
    tar.exe -czf $TempArchive $ItemsToInclude
    $sizeMB = [math]::Round((Get-Item $TempArchive).Length / 1MB, 2)
    Write-Host "[+] Pacote pronto: $sizeMB MB" -ForegroundColor Green
}
finally {
    Pop-Location
}

# Upload para a VPS via SCP
Write-Host "[*] Enviando pacote para o servidor..." -ForegroundColor Yellow
scp.exe -o StrictHostKeyChecking=accept-new $TempArchive "root@${ServerIp}:/root/deploy_package.tar.gz"

# Extracao e Deploy remoto direto
Write-Host "[*] Subindo conteineres na VPS..." -ForegroundColor Yellow
$RemoteCommand = @"
mkdir -p /opt/eleicao2026
tar -xzf /root/deploy_package.tar.gz -C /opt/eleicao2026
rm -f /root/deploy_package.tar.gz
cd /opt/eleicao2026
docker compose up -d --build
docker compose restart caddy
docker compose ps
"@

ssh.exe -o StrictHostKeyChecking=accept-new "root@$ServerIp" $RemoteCommand

# Limpeza do arquivo temporario local
Remove-Item $TempArchive -Force
Write-Host "========================================" -ForegroundColor Green
Write-Host "[+] DEPLOY CONCLUIDO COM SUCESSO!" -ForegroundColor Green
Write-Host "Acesse seu painel em: https://radareleitoral.dominiodigital.dev.br" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
