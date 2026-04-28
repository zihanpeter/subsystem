$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Set-Location $projectRoot
$serverProcess = Start-Process -FilePath "python" -ArgumentList "deploy/run_local_server.py" -WorkingDirectory $projectRoot -PassThru

Start-Sleep -Seconds 2

try {
    & (Join-Path $PSScriptRoot "start_tunnel.ps1")
}
finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id
    }
}
