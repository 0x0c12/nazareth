$root = "C:\dev\nazareth"
$env = "env"

if (Test-Path -Path (Join-Path $root $env))
{
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    . (Join-Path $root "env\Scripts\Activate.ps1")
}

Push-Location (Join-Path $root "src")
python (Join-Path $root "src/nazareth.py")
Pop-Location
