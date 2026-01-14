param(
  [int]$Port = 8000,
  [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "restart_local.ps1") -Port $Port -BindHost $BindHost -Reload
