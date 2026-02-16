$root = "C:\dev\nazareth"

$token = (Get-Content (Join-Path $root "token.txt") -Raw).TrimEnd("`r", "`n")

python (Join-Path $root "src\main.py") "$token"
