<#
.SYNOPSIS
  Stellt WSL2 auf gespiegeltes Netzwerk (networkingMode=mirrored) um, damit WSL das Heimnetz
  inkl. Multicast sieht (z. B. für die Sonos-Erkennung).

.DESCRIPTION
  - Sichert die bestehende .wslconfig (bzw. merkt sich, dass es keine gab) und den Firewall-Wert
    in %USERPROFILE%\.wslconfig.sonos-backup.json – das Rückgängig-Skript nutzt diese Sicherung.
  - Setzt im Abschnitt [wsl2] networkingMode=mirrored; andere Einstellungen bleiben erhalten.
  - Optional (nur als Administrator): erlaubt eingehende Verbindungen zur WSL-VM in der
    Hyper-V-Firewall, damit Antworten der Lautsprecher ankommen.
  - Fragt zum Schluss, ob WSL neu gestartet werden soll.

.PARAMETER NoFirewall
  Firewall nicht anfassen.
.PARAMETER NoRestart
  WSL nicht neu starten (Änderung greift erst nach "wsl --shutdown").
.PARAMETER ProfilePath
  Benutzerprofil, in dem die .wslconfig liegt (Standard: aktuelles Profil). Nur nötig, wenn das
  Skript mit einem anderen (Admin-)Konto läuft als dem, mit dem du WSL nutzt.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\wsl-mirrored-einrichten.ps1
#>
param(
  [switch]$NoFirewall,
  [switch]$NoRestart,
  [string]$ProfilePath = $env:USERPROFILE
)
$ErrorActionPreference = 'Stop'

$cfg   = Join-Path $ProfilePath '.wslconfig'
$state = Join-Path $ProfilePath '.wslconfig.sonos-backup.json'
$vmId  = '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}'   # feste ID der WSL-VM für die Hyper-V-Firewall
$utf8  = New-Object System.Text.UTF8Encoding $false
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "WSL-Konfiguration: $cfg" -ForegroundColor Cyan

# ---------------------------------------------------------------- Sicherung
if (Test-Path $state) {
  $backup = Get-Content $state -Raw | ConvertFrom-Json
  Write-Host 'Sicherung existiert bereits (Einrichtung lief schon einmal) – sie wird nicht überschrieben.'
} else {
  $backup = [pscustomobject]@{
    wslconfigExisted = Test-Path $cfg
    wslconfig        = if (Test-Path $cfg) { [IO.File]::ReadAllText($cfg) } else { $null }
    firewall         = $null
    created          = (Get-Date).ToString('s')
  }
}
function Save-Backup { [IO.File]::WriteAllText($state, ($backup | ConvertTo-Json), $utf8) }
Save-Backup

# ---------------------------------------------------------------- .wslconfig anpassen
$lines = if (Test-Path $cfg) { [IO.File]::ReadAllLines($cfg) } else { @() }
$out = New-Object System.Collections.Generic.List[string]
$inWsl2 = $false; $hasSection = $false; $done = $false
foreach ($l in $lines) {
  if ($l -match '^\s*\[(.+)\]\s*$') {
    if ($inWsl2 -and -not $done) { $out.Add('networkingMode=mirrored'); $done = $true }
    $inWsl2 = $Matches[1].Trim() -ieq 'wsl2'
    if ($inWsl2) { $hasSection = $true }
    $out.Add($l); continue
  }
  if ($inWsl2 -and $l -match '^\s*networkingMode\s*=') {
    if (-not $done) { $out.Add('networkingMode=mirrored'); $done = $true }
    continue
  }
  $out.Add($l)
}
if ($inWsl2 -and -not $done) { $out.Add('networkingMode=mirrored'); $done = $true }
if (-not $hasSection) {
  if ($out.Count -gt 0) { $out.Add('') }
  $out.Add('[wsl2]'); $out.Add('networkingMode=mirrored')
}
[IO.File]::WriteAllText($cfg, (($out -join "`r`n") + "`r`n"), $utf8)
Write-Host 'networkingMode=mirrored gesetzt.' -ForegroundColor Green

# ---------------------------------------------------------------- Firewall (optional)
if (-not $NoFirewall) {
  if ($isAdmin) {
    try {
      if ($null -eq $backup.firewall) {
        $backup.firewall = (Get-NetFirewallHyperVVMSetting -Name $vmId).DefaultInboundAction.ToString()
        Save-Backup
      }
      Set-NetFirewallHyperVVMSetting -Name $vmId -DefaultInboundAction Allow
      Write-Host "Hyper-V-Firewall: eingehend für WSL erlaubt (vorher: $($backup.firewall))." -ForegroundColor Green
    } catch {
      Write-Warning "Firewall konnte nicht angepasst werden: $($_.Exception.Message)"
    }
  } else {
    Write-Host 'Firewall übersprungen (keine Administratorrechte). Nur nötig, falls die Lautsprecher' -ForegroundColor Yellow
    Write-Host 'nach dem Umstellen nicht automatisch gefunden werden – dann dieses Skript als Administrator erneut starten.' -ForegroundColor Yellow
  }
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
