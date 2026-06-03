# Apply ai-agent-config -> live Claude/Codex (Windows). Idempotent.
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Repo
Write-Host "== ai-agent-config install (pull/apply) =="

# 1) deps check (warn only)
foreach ($c in @("git","python","claude","codex","uv")) {
  if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { Write-Host "  WARN: '$c' not found" }
}
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) { Write-Host "  WARN: 'bun' not found (gstack needs it)" }

# 2) secrets
if (-not (Test-Path ".env")) {
  Write-Host "  No .env -> copying templates/.env.example. Fill it then re-run."
  Copy-Item "templates/.env.example" ".env"
  exit 1
}
Get-Content ".env" | ForEach-Object {
  if ($_ -match '^\s*([^#=]+)=(.*)$') {
    $k=$matches[1].Trim(); $v=$matches[2].Trim()
    Set-Item -Path "Env:$k" -Value $v
    [Environment]::SetEnvironmentVariable($k, $v, "User")  # persist
  }
}

# 3) file apply
python "scripts/apply.py"

# 4) plugins (Claude)
$mk = @("revfactory/harness","JuliusBrussee/caveman","$Repo\claude\personal-local")
foreach ($m in $mk) { claude plugin marketplace add $m 2>$null }
$pl = @("harness@harness-marketplace","caveman@caveman","superpowers@claude-plugins-official","gstack@personal-local","mattpocock-skills@personal-local")
foreach ($p in $pl) { claude plugin install $p 2>$null }

# 5) external installers
if (Get-Command uv -ErrorAction SilentlyContinue) {
  uv tool install graphifyy 2>$null
  graphify install --platform windows 2>$null
  graphify install --platform codex 2>$null
}
# gstack bins (needs bun + git-bash for ./setup).
# Core repo at ~/.gstack/core; ~/.claude/skills/gstack is a junction to it.
if (Get-Command bun -ErrorAction SilentlyContinue) {
  $gsCore = "$HOME\.gstack\core"; $gsLink = "$HOME\.claude\skills\gstack"
  if (-not (Test-Path "$gsCore\browse")) { git clone --depth 1 https://github.com/garrytan/gstack $gsCore }
  New-Item -ItemType Directory -Force -Path "$HOME\.claude\skills" | Out-Null
  if (Test-Path $gsLink) { Remove-Item -Recurse -Force $gsLink }
  New-Item -ItemType Junction -Path $gsLink -Target $gsCore | Out-Null
  & "C:\Program Files\Git\bin\bash.exe" -lc "cd ~/.claude/skills/gstack && ./setup && ./setup --host codex" 2>$null
}

# prune gstack-installed top-level skills: use the personal-local PLUGIN
# (gstack:*/mattpocock-skills:*) as the single source. Keep only gstack engine + graphify.
$skillsDir = "$HOME\.claude\skills"
if (Test-Path $skillsDir) {
  Get-ChildItem -Force $skillsDir | Where-Object { $_.Name -notin @("gstack","graphify") } | ForEach-Object {
    Remove-Item -Recurse -Force -- $_.FullName
  }
}

# 6) Codex superpowers
codex plugin marketplace add obra/superpowers 2>$null

# 7) korean descriptions
python "$HOME\.claude\tools\apply-ko-desc.py" 2>$null

# 8) verify
Write-Host "== verify =="
claude plugin list 2>$null | Select-String "@|enabled"
Write-Host "Done. Restart Claude Code and Codex. Approve Codex global hook trust on first run."
