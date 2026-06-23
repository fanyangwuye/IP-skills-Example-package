# Load .env into the current PowerShell session.
# Usage:  . .\load_env.ps1     (note the leading dot + space, so vars persist in your shell)
param([string]$Path = "$PSScriptRoot\.env")

if (-not (Test-Path $Path)) {
    Write-Host "[load_env] .env not found at $Path" -ForegroundColor Yellow
    return
}

$count = 0
Get-Content $Path | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $name = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim()
    if ($value -eq "") { return }
    Set-Item -Path "Env:$name" -Value $value
    $count++
}
Write-Host "[load_env] loaded $count variables from $Path" -ForegroundColor Green
