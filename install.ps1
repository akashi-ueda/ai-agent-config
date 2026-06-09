# Apply personal-agent-config -> live Claude/Codex (Windows). Idempotent.
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Repo
Write-Host "== personal-agent-config install (pull/apply) =="

# 1) deps check (warn only)
function Pick-Command($Primary, $Fallback) {
  if (Get-Command $Primary -ErrorAction SilentlyContinue) { return $Primary }
  if (Get-Command $Fallback -ErrorAction SilentlyContinue) { return $Fallback }
  return $null
}

$PythonBin = Pick-Command "python" "python3"
$PipBin = Pick-Command "pip" "pip3"
$Env:PATH = "$HOME\.local\bin;$Env:PATH"

# pip fallback: many Windows installs expose pip only via `python -m pip`
$UsePyPip = $false
if (-not $PipBin -and $PythonBin) {
  & $PythonBin -m pip --version *> $null
  if ($LASTEXITCODE -eq 0) { $UsePyPip = $true }
}
function Invoke-Pip {
  if ($UsePyPip) { & $PythonBin -m pip @args } else { & $PipBin @args }
}

$missing = $false
foreach ($c in @("git","node","claude","codex")) {
  if (-not (Get-Command $c -ErrorAction SilentlyContinue)) {
    Write-Host "  ERROR: '$c' not found"
    $missing = $true
  }
}
if (-not $PythonBin) {
  Write-Host "  ERROR: 'python'/'python3' not found"
  $missing = $true
}
if (-not $PipBin -and -not $UsePyPip) {
  Write-Host "  ERROR: 'pip'/'pip3' not found (and 'python -m pip' unavailable)"
  $missing = $true
}
if ($missing) { exit 1 }
$PythonBin = if ($PythonBin) { $PythonBin } else { "python" }
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) { Write-Host "  WARN: 'bun' not found (gstack build needs it)" }

# 2) secrets
$GithubMcpEnv = Join-Path $HOME ".config\github-mcp\env"
function Import-AgentEnv($Path) {
  Get-Content $Path | ForEach-Object {
    if ($_ -match '^\s*(?:export\s+)?([^#=]+)=(.*)$') {
      $k=$matches[1].Trim(); $v=$matches[2].Trim()
      if (($v.Length -ge 2) -and (($v[0] -eq '"' -and $v[$v.Length - 1] -eq '"') -or ($v[0] -eq "'" -and $v[$v.Length - 1] -eq "'"))) {
        $v = $v.Substring(1, $v.Length - 2)
      }
      Set-Item -Path "Env:$k" -Value $v
      [Environment]::SetEnvironmentVariable($k, $v, "User")  # persist
    }
  }
}

if (Test-Path ".env") {
  Import-AgentEnv ".env"
} elseif (Test-Path $GithubMcpEnv) {
  Import-AgentEnv $GithubMcpEnv
} else {
  Write-Host "  No .env or ~/.config/github-mcp/env -> copying .env.example. Fill it then re-run."
  Copy-Item ".env.example" ".env"
  exit 1
}
if (-not $Env:GITHUB_PERSONAL_ACCESS_TOKEN -and (Test-Path $GithubMcpEnv)) {
  Import-AgentEnv $GithubMcpEnv
}
if (-not $Env:GITHUB_PERSONAL_ACCESS_TOKEN) {
  Write-Host "  ERROR: GITHUB_PERSONAL_ACCESS_TOKEN is empty"
  exit 1
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $GithubMcpEnv) | Out-Null
$escapedGithubToken = $Env:GITHUB_PERSONAL_ACCESS_TOKEN.Replace("'", "''")
Set-Content -Path $GithubMcpEnv -Value "export GITHUB_PERSONAL_ACCESS_TOKEN='$escapedGithubToken'" -NoNewline -Encoding utf8

# 3) file apply (place files, merge MCP/config)
& $PythonBin "scripts/apply.py"

# 4) plugin install (manifest-driven engine: both hosts, externals, builds)
& $PythonBin "scripts/install_plugins.py"

# 5) korean descriptions
& $PythonBin "$HOME\.claude\tools\apply-ko-desc.py" 2>$null

# 6) verify (real install state, not just the plan)
Write-Host "== verify =="
& $PythonBin "scripts/install_plugins.py" --verify-installed
if ($LASTEXITCODE -ne 0) {
  Write-Host "  ERROR: install verification failed (a manifest plugin is not installed+enabled)"
  exit 1
}
Write-Host "Done. Restart Claude Code and Codex. Approve Codex global hook trust on first run."
