<#
.SYNOPSIS
  Lancia il server PGDCA (backend + GUI web) dal venv del progetto.

.DESCRIPTION
  Avvia `python -m pgdca.api.server` dalla root del repo (necessario per
  l'adapter llmswitch, che importa da examples/). L'event store di default
  e' pgdca.db nella root (persistente tra i riavvii); usa -Db :memory: per
  una sessione usa-e-getta.

.PARAMETER Adapter
  mock (default) | anthropic | llmswitch. Vedi docs/LOCAL_INTEGRATIONS.md
  per la configurazione di llmswitch (registro provider + variabili).

.EXAMPLE
  .\scripts\run.ps1
  .\scripts\run.ps1 -Adapter llmswitch
  .\scripts\run.ps1 -Adapter llmswitch -DbPath :memory: -Port 8010 -Open
#>
[CmdletBinding()]
param(
    [ValidateSet("mock", "anthropic", "llmswitch")]
    [string]$Adapter = "mock",
    # non "-Db": collide con l'alias del common parameter -Debug
    [string]$DbPath = "pgdca.db",
    [int]$Port = 8000,
    [switch]$Open
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$venvPy = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    throw "venv non trovato: esegui prima .\scripts\install.ps1"
}

if ($Adapter -eq "llmswitch") {
    & $venvPy -c "import llmswitch" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "llmswitch non installato nel venv: .\scripts\install.ps1 (o pip install -e C:\Projects\llmswitch)"
    }
}

if ($Open) {
    Start-Job -ScriptBlock {
        param($u) Start-Sleep -Seconds 2; Start-Process $u
    } -ArgumentList "http://127.0.0.1:$Port" | Out-Null
}

Write-Host "PGDCA su http://127.0.0.1:$Port (adapter: $Adapter, db: $DbPath) - Ctrl+C per fermare"
& $venvPy -m pgdca.api.server --adapter $Adapter --db $DbPath --port $Port
