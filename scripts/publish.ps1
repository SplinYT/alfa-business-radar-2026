$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$account = gh api user --jq .login
if ($LASTEXITCODE -ne 0) { throw "Run gh auth login first" }
Write-Host "Publishing private repository under $account"
gh repo create "$account/alfa-business-radar-2026" --private --source=. --remote=origin --description "Business news analytics prototype for Alfa Hack 2026"
if ($LASTEXITCODE -ne 0) { throw "Repository was not created. Inspect error; no push attempted." }
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw "Push failed" }
git push origin v0.1.0
if ($LASTEXITCODE -ne 0) { throw "Tag push failed" }
gh repo view --web
