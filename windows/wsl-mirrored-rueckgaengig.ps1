<#
.SYNOPSIS
  Macht die Umstellung auf networkingMode=mirrored rückgängig.

.DESCRIPTION
  - Entfernt networkingMode=mirrored aus [wsl2]. Gab es vorher einen anderen Wert, wird dieser
    wiederhergestellt. Spätere eigene Änderungen an der .wslconfig bleiben erhalten.
  - Gab es vorher keine .wslconfig und steht nichts anderes mehr darin, wird die Datei gelöscht.
  - Setzt die Hyper-V-Firewall auf den gesicherten Wert zurück (nur als Administrator).
  - Fragt zum Schluss, ob WSL neu gestartet werden soll.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\wsl-mirrored-rueckgaengig.ps1
#>
param(
  [switch]$NoRestart,
  [string]$ProfilePath = $env:USERPROFILE
)
$ErrorActionPreference = 'Stop'

$cfg   = Join-Path $ProfilePath '.wslconfig'
$state = Join-Path $ProfilePath '.wslconfig.sonos-backup.json'
$vmId  = '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'
$utf8  = New-Object System.Text.UTF8Encoding $false
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)

$backup = $null
if (Test-Path $state) {
  $backup = Get-Content $state -Raw | ConvertFrom-Json
} else {
  Write-Warning "Keine Sicherung gefunden ($state). Entferne nur networkingMode=mirrored."
}

# ---------------------------------------------------------------- ursprünglichen networkingMode ermitteln
$original = $null
if ($backup -and $backup.wslconfig) {
  $sec = ''
  foreach ($l in ($backup.wslconfig -split "`r?`n")) {
    if ($l -match '^\s*\[(.+)\]\s*$') { $sec = $Matches[1].Trim(); continue }
    if ($sec -ieq 'wsl2' -and $l -match '^\s*networkingMode\s*=\s*(.+?)\s*$') { $original = $Matches[1] }
  }
}

# ---------------------------------------------------------------- .wslconfig zurücksetzen
if (Test-Path $cfg) {
  $out = New-Object System.Collections.Generic.List[string]
  $inWsl2 = $false
  foreach ($l in [IO.File]::ReadAllLines($cfg)) {
    if ($l -match '^\s*\[(.+)\]\s*$') { $inWsl2 = $Matches[1].Trim() -ieq 'wsl2'; $out.Add($l); continue }
    if ($inWsl2 -and $l -match '^\s*networkingMode\s*=') {
      if ($original) { $out.Add("networkingMode=$original") }
      continue
    }
    $out.Add($l)
  }
  $meaningful = $out | Where-Object { $_.Trim() -ne '' -and $_.Trim() -notmatch '^\[wsl2\]$' -and $_.Trim() -notmatch '^[#;]' }
  if ($backup -and -not $backup.wslconfigExisted -and -not $meaningful) {
    Remove-Item $cfg
    Write-Host '.wslconfig gelöscht (gab es vorher nicht).' -ForegroundColor Green
  } else {
    [IO.File]::WriteAllText($cfg, (($out -join "`r`n") + "`r`n"), $utf8)
    if ($original) { Write-Host "networkingMode=$original wiederhergestellt." -ForegroundColor Green }
    else { Write-Host 'networkingMode entfernt (WSL nutzt wieder den Standard NAT).' -ForegroundColor Green }
  }
} else {
  Write-Host 'Keine .wslconfig vorhanden – nichts zu tun.'
}

# ---------------------------------------------------------------- Firewall zurücksetzen
$firewallPending = $false
if ($backup -and $backup.firewall) {
  if ($isAdmin) {
    try {
      Set-NetFirewallHyperVVMSetting -Name $vmId -DefaultInboundAction $backup.firewall
      Write-Host "Hyper-V-Firewall auf '$($backup.firewall)' zurückgesetzt." -ForegroundColor Green
    } catch {
      $firewallPending = $true
      Write-Warning "Firewall konnte nicht zurückgesetzt werden: $($_.Exception.Message)"
    }
  } else {
    $firewallPending = $true
    Write-Host "Die Firewall wurde bei der Einrichtung geändert. Zum Zurücksetzen dieses Skript als Administrator erneut starten." -ForegroundColor Yellow
  }
}

# Sicherung nur löschen, wenn nichts mehr offen ist
if ($backup -and -not $firewallPending) {
  Remove-Item $state
  Write-Host 'Sicherung entfernt.'
}

# ---------------------------------------------------------------- Neustart
if ($NoRestart) {
  Write-Host 'Fertig. Wirksam nach: wsl --shutdown'
  return
}
Write-Host ''
Write-Host 'Achtung: Ein Neustart beendet ALLE laufenden WSL-Fenster und -Dienste (auch Docker in WSL).' -ForegroundColor Yellow
$answer = Read-Host 'WSL jetzt neu starten? (j/n)'
if ($answer -match '^[jJyY]') {
  wsl.exe --shutdown
  Write-Host 'WSL wurde beendet. Öffne dein Ubuntu-Terminal einfach neu.' -ForegroundColor Green
} else {
  Write-Host 'Fertig. Wirksam nach: wsl --shutdown'
}
