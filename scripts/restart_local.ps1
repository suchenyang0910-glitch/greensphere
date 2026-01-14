param(
  [int]$Port = 8000,
  [string]$BindHost = "127.0.0.1",
  [string]$App = "main:app",
  [switch]$Reload
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Get-ListeningPids([int]$port) {
  $pids = @()

  try {
    $pids = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop | ForEach-Object { $_.OwningProcess } | Sort-Object -Unique)
    if ($pids.Count -gt 0) { return $pids }
  } catch {
  }

  try {
    $lines = netstat -ano | Select-String -SimpleMatch ":$port" | ForEach-Object { $_.Line }
    foreach ($line in $lines) {
      if ($line -notmatch "LISTENING") { continue }
      $tokens = $line -split "\s+" | Where-Object { $_ -ne "" }
      if ($tokens.Count -lt 2) { continue }
      $pidToken = $tokens[-1]
      if ($pidToken -match "^\d+$") { $pids += [int]$pidToken }
    }
    $pids = @($pids | Sort-Object -Unique)
  } catch {
  }

  return $pids
}

$pids = Get-ListeningPids -port $Port
foreach ($procId in $pids) {
  try {
    Stop-Process -Id $procId -Force -ErrorAction Stop
  } catch {
  }
}

$args = @("-m", "uvicorn", $App, "--host", $BindHost, "--port", "$Port")
if ($Reload) { $args += "--reload" }

& python @args

