param(
    [string]$TokenFile = "secrets/cloudflared_token.txt"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$tokenPath = Join-Path $projectRoot $TokenFile

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    throw "cloudflared not found. Install it first: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
}

if (-not (Test-Path $tokenPath)) {
    throw "Token file not found: $tokenPath"
}

$token = (Get-Content -Raw -Path $tokenPath).Trim()
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Tunnel token file is empty: $tokenPath"
}

Set-Location $projectRoot
cloudflared tunnel run --token $token
