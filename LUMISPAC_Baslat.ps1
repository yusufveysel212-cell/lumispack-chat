$ErrorActionPreference = 'Stop'
$python = Join-Path $env:LOCALAPPDATA 'LUMISPAC\runtime\venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'LUMISPAC runtime Python bulunamadi.' }
Start-Process -FilePath $python -ArgumentList ('"' + (Join-Path $PSScriptRoot 'LUMISPAC_Launcher.py') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
