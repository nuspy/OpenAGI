<#
.SYNOPSIS
  Launcher grafico di PGDCA: scegli le opzioni e avvia server + GUI web.

  Doppio clic (o `.\runapp.ps1`) -> finestra con le scelte -> Avvia.
  Il server parte in una sua console (Ctrl+C per fermarlo) e il browser
  si apre sulla GUI. Il provider LLM si sceglie DENTRO la GUI, tab LLM.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$venvPy = Join-Path $repo ".venv\Scripts\python.exe"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

# --- finestra ----------------------------------------------------------------
$form = New-Object System.Windows.Forms.Form
$form.Text = "PGDCA — Avvio"
$form.Size = New-Object System.Drawing.Size(560, 560)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

function Add-Label([string]$text, [int]$x, [int]$y, [int]$w, [bool]$bold = $false, [bool]$muted = $false) {
    $l = New-Object System.Windows.Forms.Label
    $l.Text = $text; $l.Location = New-Object System.Drawing.Point($x, $y)
    $l.Size = New-Object System.Drawing.Size($w, 34)
    if ($bold) { $l.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold) }
    if ($muted) { $l.ForeColor = [System.Drawing.Color]::DimGray; $l.Font = New-Object System.Drawing.Font("Segoe UI", 8.5) }
    $form.Controls.Add($l); return $l
}
function Add-Radio([string]$text, [int]$x, [int]$y, [int]$w, [bool]$checked = $false) {
    $r = New-Object System.Windows.Forms.RadioButton
    $r.Text = $text; $r.Location = New-Object System.Drawing.Point($x, $y)
    $r.Size = New-Object System.Drawing.Size($w, 24); $r.Checked = $checked
    return $r
}

$y = 12
Add-Label "Mondo" 16 $y 200 $true | Out-Null; $y += 24
$grpWorld = New-Object System.Windows.Forms.Panel
$grpWorld.Location = New-Object System.Drawing.Point(16, $y)
$grpWorld.Size = New-Object System.Drawing.Size(510, 52)
$rWorldToy   = Add-Radio "Scenario di prova (montagna): guarda il sistema lavorare" 0 0 500 $true
$rWorldEmpty = Add-Radio "Mondo vuoto: i goal li metti tu dalla GUI" 0 26 500
$grpWorld.Controls.AddRange(@($rWorldToy, $rWorldEmpty)); $form.Controls.Add($grpWorld); $y += 62

Add-Label "Porte verso il mondo esterno (telefono, email, ...)" 16 $y 500 $true | Out-Null; $y += 24
$grpPorts = New-Object System.Windows.Forms.Panel
$grpPorts.Location = New-Object System.Drawing.Point(16, $y)
$grpPorts.Size = New-Object System.Drawing.Size(510, 78)
$rPortsOff  = Add-Radio "Disattive (solo il mercato di prova)" 0 0 500 $true
$rPortsMock = Add-Radio "Finte (mock): l'agente le usa, il mondo reale non viene toccato" 0 26 500
$rPortsReal = Add-Radio "Voce REALE via CallAPICall (:8770): le chiamate approvate squillano davvero" 0 52 500
$grpPorts.Controls.AddRange(@($rPortsOff, $rPortsMock, $rPortsReal)); $form.Controls.Add($grpPorts); $y += 88

Add-Label "Memoria (event store)" 16 $y 250 $true | Out-Null; $y += 24
$tDb = New-Object System.Windows.Forms.TextBox
$tDb.Location = New-Object System.Drawing.Point(16, $y)
$tDb.Size = New-Object System.Drawing.Size(360, 28)
$tDb.Text = "pgdca.db"
$form.Controls.Add($tDb)
$cbTemp = New-Object System.Windows.Forms.CheckBox
$cbTemp.Text = "usa e getta"
$cbTemp.Location = New-Object System.Drawing.Point(390, $y)
$cbTemp.Size = New-Object System.Drawing.Size(130, 28)
$cbTemp.Add_CheckedChanged({ $tDb.Enabled = -not $cbTemp.Checked })
$form.Controls.Add($cbTemp); $y += 30
Add-Label "Stesso file = il sistema riprende da dove era rimasto (goal, budget, decisioni)." 16 $y 510 $false $true | Out-Null; $y += 30

Add-Label "Porta web" 16 $y 120 $true | Out-Null
$nPort = New-Object System.Windows.Forms.NumericUpDown
$nPort.Location = New-Object System.Drawing.Point(110, $y)
$nPort.Size = New-Object System.Drawing.Size(90, 28)
$nPort.Minimum = 1024; $nPort.Maximum = 65535; $nPort.Value = 8000
$form.Controls.Add($nPort)
$cbBrowser = New-Object System.Windows.Forms.CheckBox
$cbBrowser.Text = "apri il browser sulla GUI"
$cbBrowser.Location = New-Object System.Drawing.Point(230, $y)
$cbBrowser.Size = New-Object System.Drawing.Size(240, 28)
$cbBrowser.Checked = $true
$form.Controls.Add($cbBrowser); $y += 40

Add-Label ("Il PROVIDER LLM (LM Studio, chiavi API, Anthropic, ...) si sceglie nella GUI" +
           " web, tab LLM: registro llmswitch. Motore di riserva senza llmswitch: mock.") 16 $y 510 $false $true | Out-Null
$y += 40

# --- pulsanti ----------------------------------------------------------------
$btnStart = New-Object System.Windows.Forms.Button
$btnStart.Text = "Avvia"
$btnStart.Location = New-Object System.Drawing.Point(16, $y)
$btnStart.Size = New-Object System.Drawing.Size(150, 40)
$btnStart.BackColor = [System.Drawing.Color]::FromArgb(79, 70, 229)
$btnStart.ForeColor = [System.Drawing.Color]::White
$form.Controls.Add($btnStart)

$btnStop = New-Object System.Windows.Forms.Button
$btnStop.Text = "Ferma server"
$btnStop.Location = New-Object System.Drawing.Point(180, $y)
$btnStop.Size = New-Object System.Drawing.Size(150, 40)
$form.Controls.Add($btnStop)

$btnClose = New-Object System.Windows.Forms.Button
$btnClose.Text = "Chiudi"
$btnClose.Location = New-Object System.Drawing.Point(376, $y)
$btnClose.Size = New-Object System.Drawing.Size(150, 40)
$btnClose.Add_Click({ $form.Close() })
$form.Controls.Add($btnClose)
$y += 50

$status = Add-Label "" 16 $y 510 $false $true

function Get-ServerPid([int]$port) {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return $c.OwningProcess } else { return $null }
}

$btnStart.Add_Click({
    if (-not (Test-Path $venvPy)) {
        [System.Windows.Forms.MessageBox]::Show(
            "Ambiente non installato: esegui prima scripts\install.ps1",
            "PGDCA", "OK", "Warning") | Out-Null
        return
    }
    $port = [int]$nPort.Value
    if (Get-ServerPid $port) {
        $status.Text = "C'e' gia' un server sulla porta $port (usa Ferma server, o cambia porta)."
        return
    }
    $args = @("-m", "pgdca.api.server", "--port", "$port",
              "--db", $(if ($cbTemp.Checked) { ":memory:" } else { $tDb.Text.Trim() }))
    if ($rWorldEmpty.Checked) { $args += "--empty" }
    if ($rPortsMock.Checked)  { $args += "--mock-ports" }
    if ($rPortsReal.Checked)  { $args += @("--voice", "callapicall") }
    # console visibile: i log si vedono e Ctrl+C ferma il server
    Start-Process -FilePath $venvPy -ArgumentList $args -WorkingDirectory $repo | Out-Null
    $status.Text = "Avviato su http://127.0.0.1:$port ..."
    if ($cbBrowser.Checked) {
        Start-Job -ScriptBlock { param($u) Start-Sleep 3; Start-Process $u } `
                  -ArgumentList "http://127.0.0.1:$port" | Out-Null
    }
})

$btnStop.Add_Click({
    $port = [int]$nPort.Value
    $procId = Get-ServerPid $port
    if ($procId) {
        Stop-Process -Id $procId -Force -Confirm:$false
        $status.Text = "Server sulla porta $port fermato (PID $procId)."
    } else {
        $status.Text = "Nessun server in ascolto sulla porta $port."
    }
})

[void]$form.ShowDialog()
