# Apply ai-agent-config -> live Claude/Codex (Windows). Idempotent.
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Repo
Write-Host "== ai-agent-config install (pull/apply) =="

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

function Invoke-ClaudeCli {
  & claude @args
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

# 3) file apply
& $PythonBin "scripts/apply.py"

# 4) plugins (Claude)
$mk = @("revfactory/harness","JuliusBrussee/caveman","anthropics/claude-plugins-official","openai/codex-plugin-cc","akashi-ueda/agent-attribution","$Repo\claude\personal-local")
foreach ($m in $mk) { Invoke-ClaudeCli plugin marketplace add $m 2>$null }
$pl = @("harness@harness-marketplace","caveman@caveman","superpowers@claude-plugins-official","codex@openai-codex","gstack@personal-local","mattpocock-skills@personal-local","graphify@personal-local","reply-trace@reply-trace")
# install/enable are idempotent: a benign "already enabled" goes to stderr and must
# not abort the run under $ErrorActionPreference=Stop.
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
foreach ($p in $pl) {
  Invoke-ClaudeCli plugin install $p 2>$null
  Invoke-ClaudeCli plugin enable $p 2>$null
}
$ErrorActionPreference = $prevEAP

# 5) external CLIs/binaries only. Do not register standalone agent skills.
if (-not (Get-Command graphify -ErrorAction SilentlyContinue)) {
  if ($PipBin -or $UsePyPip) {
    Invoke-Pip install --user graphifyy
    if ($LASTEXITCODE -ne 0) { Invoke-Pip install --user --break-system-packages graphifyy }
  }
  if (-not (Get-Command graphify -ErrorAction SilentlyContinue)) {
    # On Windows the user Scripts dir is versioned (…\Python\PythonXY\Scripts), not …\Python\Scripts.
    $scriptsDir = (& $PythonBin -c "import sysconfig;print(sysconfig.get_path('scripts','nt_user'))" 2>$null)
    $graphifyExe = Join-Path $scriptsDir "graphify.exe"
    if (Test-Path $graphifyExe) {
      New-Item -ItemType Directory -Force -Path "$HOME\.local\bin" | Out-Null
      $shim = "@echo off`r`n`"$graphifyExe`" %*`r`n"
      Set-Content -Path "$HOME\.local\bin\graphify.cmd" -Value $shim -NoNewline -Encoding ascii
    }
  }
}
# gstack core lives outside every agent's skills dir. Plugin skills resolve bins from here.
if (Get-Command bun -ErrorAction SilentlyContinue) {
  # gstack build runs `bash scripts/build.sh`; on Windows bash ships with Git but is off PATH.
  if (-not (Get-Command bash -ErrorAction SilentlyContinue)) {
    $gitDir = Split-Path -Parent (Split-Path -Parent (Get-Command git).Source)  # ...\Git
    $gitBash = Join-Path $gitDir "usr\bin"
    if (Test-Path (Join-Path $gitBash "bash.exe")) { $Env:PATH = "$gitBash;$Env:PATH" }
    else { Write-Host "  WARN: 'bash' not found; gstack build will be skipped (plugin uses repo skill copy)" }
  }
  if (Get-Command bash -ErrorAction SilentlyContinue) {
    $gsCore = "$HOME\.gstack\core"
    if (-not (Test-Path "$gsCore\browse")) { git clone --depth 1 https://github.com/garrytan/gstack $gsCore }
    Push-Location $gsCore
    try {
      bun install --frozen-lockfile 2>$null
      if ($LASTEXITCODE -ne 0) { bun install }
      bun run build
    } finally {
      Pop-Location
    }
  }
}

function Sync-CodexPlugin($Name, $Source) {
  $dst = "$HOME\.codex\plugins\$Name"
  if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Copy-Item "$Source\*" $dst -Recurse -Force
  if (Test-Path "$dst\.claude-plugin") { Remove-Item -Recurse -Force "$dst\.claude-plugin" }
  New-Item -ItemType Directory -Force -Path "$dst\.codex-plugin" | Out-Null
}

function Sync-CodexGstackPlugin {
  $dst = "$HOME\.codex\plugins\gstack"
  if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
  New-Item -ItemType Directory -Force -Path "$dst\.codex-plugin","$dst\skills" | Out-Null
  $generated = "$HOME\.gstack\core\.agents\skills"
  if (Test-Path $generated) {
    Copy-Item "$generated\*" "$dst\skills" -Recurse -Force
    Get-ChildItem "$dst\skills" -Recurse -Filter "SKILL.md" | ForEach-Object {
      $text = Get-Content $_.FullName -Raw
      $text = $text -replace '\$HOME/\.codex/skills/gstack', '$HOME/.gstack/core'
      $text = $text -replace '\$HOME/\.agents/skills/gstack', '$HOME/.gstack/core'
      $text = $text -replace '\.agents/skills/gstack', '$HOME/.gstack/core'
      Set-Content -Path $_.FullName -Value $text -NoNewline -Encoding utf8
    }
  } else {
    Copy-Item "$Repo\claude\personal-local\plugins\gstack\skills\*" "$dst\skills" -Recurse -Force
  }
}

# 6) Codex plugins. Store plugins come from OpenAI-curated; local wrappers go through personal marketplace.
New-Item -ItemType Directory -Force -Path "$HOME\.agents\plugins","$HOME\.codex\plugins" | Out-Null
Copy-Item "$Repo\codex\personal-marketplace.json" "$HOME\.agents\plugins\marketplace.json" -Force
Sync-CodexGstackPlugin
Copy-Item "$Repo\codex\plugin-json\gstack.json" "$HOME\.codex\plugins\gstack\.codex-plugin\plugin.json" -Force
Sync-CodexPlugin "mattpocock-skills" "$Repo\claude\personal-local\plugins\mattpocock-skills"
Copy-Item "$Repo\codex\plugin-json\mattpocock-skills.json" "$HOME\.codex\plugins\mattpocock-skills\.codex-plugin\plugin.json" -Force
Sync-CodexPlugin "graphify" "$Repo\claude\personal-local\plugins\graphify"
Copy-Item "$Repo\codex\plugin-json\graphify.json" "$HOME\.codex\plugins\graphify\.codex-plugin\plugin.json" -Force
Sync-CodexPlugin "attribution" "$Repo\codex\attribution-plugin"
Copy-Item "$Repo\codex\plugin-json\attribution.json" "$HOME\.codex\plugins\attribution\.codex-plugin\plugin.json" -Force
codex plugin add superpowers@openai-curated 2>$null
codex plugin add gstack@personal 2>$null
codex plugin add mattpocock-skills@personal 2>$null
codex plugin add graphify@personal 2>$null
codex plugin add attribution@personal 2>$null

# 7) korean descriptions
& $PythonBin "$HOME\.claude\tools\apply-ko-desc.py" 2>$null

# 8) verify
Write-Host "== verify =="
Invoke-ClaudeCli plugin list 2>$null | Select-String "@|enabled"
Write-Host "Done. Restart Claude Code and Codex. Approve Codex global hook trust on first run."
