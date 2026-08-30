<#
.SYNOPSIS
  Installa PGDCA in un venv locale (.venv) su Windows.

.DESCRIPTION
  - trova un Python >= 3.11 (preferenza: py -3.12, poi py -3.11, poi python)
  - crea .venv se manca e installa il progetto editable con gli extra api+dev
  - con -Anthropic installa anche l'SDK per l'adapter di riferimento
  - se la libreria locale llmswitch esiste (default C:\Projects\llmswitch)
    la installa editable, cosi' `--adapter llmswitch` funziona subito
  - con -RunTests esegue pytest a fine installazione

.EXAMPLE
  .\scripts\install.ps1
  .\scripts\install.ps1 -Anthropic -RunTests
  .\scripts\install.ps1 -LlmswitchPath D:\lib\llmswitch
#>
[CmdletBinding()]
param(
    [string]$LlmswitchPath = "C:\Projects\llmswitch",
    [switch]$Anthropic,
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# --- interprete: serve >= 3.11 (il 3.10 di sistema NON va bene) -------------
function Find-Python {
    foreach ($args in @(@("-3.12"), @("-3.11"))) {
        $py = Get-Command py -ErrorAction SilentlyContinue
        if ($py) {
            & py @args -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) { return @("py") + $args }
        }
    }
    $p = Get-Command python -ErrorAction SilentlyContinue
    if ($p) {
        $ok = & python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
        if ($LASTEXITCODE -eq 0) { return @("python") }
    }
    throw "Nessun Python >= 3.11 trovato (il progetto richiede 3.11+; installa Python 3.12)."
}

$venvPy = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    $launcher = Find-Python
    Write-Host "Creo il venv con: $($launcher -join ' ')"
    $exe = $launcher[0]
    $extra = @()
    if ($launcher.Count -gt 1) { $extra = @($launcher[1..($launcher.Count - 1)]) }
    & $exe @extra -m venv (Join-Path $repo ".venv")
}
& $venvPy -c "import sys; print('venv:', sys.version)"

# --- dipendenze -------------------------------------------------------------
& $venvPy -m pip install --upgrade pip --quiet
$extras = "api,dev"
if ($Anthropic) { $extras += ",anthropic" }
Write-Host "Installo pgdca editable con extra [$extras]..."
& $venvPy -m pip install -e ".[$extras]" --quiet

# --- integrazione locale llmswitch (facoltativa) ----------------------------
if (Test-Path (Join-Path $LlmswitchPath "pyproject.toml")) {
    Write-Host "Installo llmswitch editable da $LlmswitchPath..."
    & $venvPy -m pip install -e $LlmswitchPath --quiet
} else {
    Write-Host "llmswitch non trovato in ${LlmswitchPath}: salto (l'adapter llmswitch restera' inutilizzabile finche' non lo installi)."
}

if ($RunTests) {
    Write-Host "Eseguo la suite di test..."
    & $venvPy -m pytest
}

Write-Host ""
Write-Host "Installazione completata. Avvio: .\scripts\run.ps1 [-Adapter llmswitch]"
