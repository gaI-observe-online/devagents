Set-StrictMode -Version Latest

function New-GadosInstallerState {
  param(
    [Parameter(Mandatory=$true)][string]$StatePath
  )
  return @{
    schema = "gados.windows.installer.state.v2"
    created_at_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    last_updated_at_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    steps = @{}
    blocked = $null
    last_run = $null
    state_path = $StatePath
  }
}

function Read-GadosInstallerState {
  param(
    [Parameter(Mandatory=$true)][string]$StatePath
  )
  $dir = Split-Path -Parent $StatePath
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  if (!(Test-Path $StatePath)) {
    return (New-GadosInstallerState -StatePath $StatePath)
  }
  try {
    return (Get-Content $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable)
  } catch {
    # Corrupt state should not brick installs; start fresh but keep the old file.
    $bak = $StatePath + ".corrupt." + (Get-Date).ToString("yyyyMMddHHmmss")
    Copy-Item -Force $StatePath $bak
    return (New-GadosInstallerState -StatePath $StatePath)
  }
}

function Write-GadosInstallerState {
  param(
    [Parameter(Mandatory=$true)]$State,
    [Parameter(Mandatory=$true)][string]$StatePath
  )
  $dir = Split-Path -Parent $StatePath
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $State.last_updated_at_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  ($State | ConvertTo-Json -Depth 12) | Set-Content -Path $StatePath -Encoding UTF8
}

function New-GadosLog {
  param(
    [Parameter(Mandatory=$true)][string]$LogPath,
    [scriptblock]$UiLogAppend
  )
  return @{
    path = $LogPath
    ui_append = $UiLogAppend
  }
}

function Write-GadosLog {
  param(
    [Parameter(Mandatory=$true)]$Log,
    [Parameter(Mandatory=$true)][string]$Message,
    [ValidateSet("INFO","WARN","ERROR")][string]$Level = "INFO"
  )
  $dir = Split-Path -Parent $Log.path
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $ts = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  $line = "$ts [$Level] $Message"
  Add-Content -Path $Log.path -Value $line -Encoding UTF8
  if ($null -ne $Log.ui_append) { & $Log.ui_append $line }
}

function Test-GadosIsAdmin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-GadosCmd {
  param([Parameter(Mandatory=$true)][string]$Name)
  return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-GadosCmd {
  param(
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][scriptblock]$Fn,
    [Parameter(Mandatory=$true)]$Log
  )
  Write-GadosLog -Log $Log -Message $Title -Level "INFO"
  & $Fn
}

function Get-GadosTcpPortInUse {
  param([Parameter(Mandatory=$true)][int]$Port)
  try {
    $c = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop
    return ($null -ne $c)
  } catch {
    # Get-NetTCPConnection may not exist on older SKUs; fallback to netstat parsing.
    try {
      $out = & netstat -ano | Out-String
      return $out -match "LISTENING\s+0\.0\.0\.0:$Port\s"
    } catch {
      return $false
    }
  }
}

function Get-GadosFacts {
  param(
    [Parameter(Mandatory=$true)][string]$RepoDir,
    [int]$GrafanaPort = 3000,
    [int]$ServicePort = 8000
  )

  $dockerDiag = @{
    docker_service_running = $null
    wsl_present = $null
    wsl_default_version = $null
    wsl_status = $null
    hypervisorlaunchtype = $null
    vmp_enabled = $null
    wsl_feature_enabled = $null
  }

  $facts = @{
    ps_edition = $PSVersionTable.PSEdition
    ps_version = ($PSVersionTable.PSVersion.ToString())
    is_windows = $IsWindows
    is_admin = $false
    has_winget = (Test-GadosCmd -Name "winget")
    has_git = (Test-GadosCmd -Name "git")
    has_python = (Test-GadosCmd -Name "python")
    python_version = $null
    has_docker = (Test-GadosCmd -Name "docker")
    has_docker_compose = $false
    docker_running = $false
    repo_dir_exists = (Test-Path $RepoDir)
    has_compose_test = $false
    has_compose_obs = $false
    grafana_port_in_use = (Get-GadosTcpPortInUse -Port $GrafanaPort)
    service_port_in_use = (Get-GadosTcpPortInUse -Port $ServicePort)
    docker_diag = $dockerDiag
  }

  $facts.is_admin = (Test-GadosIsAdmin)

  if ($facts.has_python) {
    try {
      $pv = & python --version 2>&1
      $facts.python_version = ($pv | Out-String).Trim()
    } catch {
      $facts.python_version = $null
    }
  }

  if ($facts.has_docker) {
    # Docker Desktop Windows service status (best-effort).
    try {
      $svc = Get-Service -Name "com.docker.service" -ErrorAction Stop
      $facts.docker_diag.docker_service_running = ($svc.Status -eq "Running")
    } catch {
      $facts.docker_diag.docker_service_running = $null
    }

    # WSL diagnostics (common cause for "engine won't start").
    try {
      & wsl.exe --status *> $null
      $facts.docker_diag.wsl_present = $true
      try {
        $status = & wsl.exe --status 2>&1 | Out-String
        $facts.docker_diag.wsl_status = $status.Trim()
        if ($status -match "Default Version:\s*(\d+)") {
          $facts.docker_diag.wsl_default_version = $Matches[1]
        }
      } catch {}
    } catch {
      $facts.docker_diag.wsl_present = $false
    }

    # Windows feature + hypervisor boot checks (best-effort).
    try {
      $bcd = & bcdedit /enum 2>$null | Out-String
      if ($bcd -match "hypervisorlaunchtype\s+(\w+)") {
        $facts.docker_diag.hypervisorlaunchtype = $Matches[1]
      }
    } catch {}
    try {
      $vmp = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -ErrorAction Stop
      $facts.docker_diag.vmp_enabled = ($vmp.State -eq "Enabled")
    } catch {}
    try {
      $wslf = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -ErrorAction Stop
      $facts.docker_diag.wsl_feature_enabled = ($wslf.State -eq "Enabled")
    } catch {}

    try {
      & docker compose version *> $null
      $facts.has_docker_compose = $true
    } catch {
      $facts.has_docker_compose = $false
    }
    try {
      & docker info *> $null
      $facts.docker_running = $true
    } catch {
      $facts.docker_running = $false
    }
  }

  if ($facts.repo_dir_exists) {
    $facts.has_compose_test = (Test-Path (Join-Path $RepoDir "compose.test.yml"))
    $facts.has_compose_obs = (Test-Path (Join-Path $RepoDir "docker-compose.yml"))
  }

  return $facts
}

function New-GadosDecision {
  param(
    [Parameter(Mandatory=$true)][ValidateSet("SKIP","APPLY","PAUSE","ABORT")][string]$Decision,
    [Parameter(Mandatory=$true)][string]$Detected,
    [Parameter(Mandatory=$true)][string]$Changed,
    [Parameter(Mandatory=$true)][string]$Action,
    [Parameter(Mandatory=$true)][string]$Resume
  )
  return @{
    decision = $Decision
    detected = $Detected
    changed = $Changed
    action = $Action
    resume = $Resume
  }
}

function New-GadosStepResult {
  param(
    [Parameter(Mandatory=$true)][string]$Id,
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][ValidateSet("PENDING","RUNNING","DONE","FAILED","SKIPPED","PAUSED","ABORTED")][string]$Status,
    [Parameter(Mandatory=$true)]$DecisionObj,
    [string]$Note = ""
  )
  return @{
    id = $Id
    title = $Title
    status = $Status
    note = $Note
    decision = $DecisionObj
    updated_at_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  }
}

function Set-GadosStepState {
  param(
    [Parameter(Mandatory=$true)]$State,
    [Parameter(Mandatory=$true)]$StepResult
  )
  if (-not $State.steps.ContainsKey($StepResult.id)) {
    $State.steps[$StepResult.id] = @{}
  }
  $State.steps[$StepResult.id] = $StepResult
}

function Invoke-GadosHttpWaitOk {
  param(
    [Parameter(Mandatory=$true)][string]$Url,
    [int]$TimeoutSeconds = 2,
    [int]$Retries = 60,
    [int]$SleepMs = 1000
  )
  for ($i = 0; $i -lt $Retries; $i++) {
    try {
      $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec $TimeoutSeconds -Uri $Url
      if ($r.StatusCode -eq 200) { return $true }
    } catch {}
    Start-Sleep -Milliseconds $SleepMs
  }
  return $false
}

function Get-GadosDesiredState {
  param(
    [Parameter(Mandatory=$true)][string]$RepoUrl,
    [Parameter(Mandatory=$true)][string]$InstallRoot,
    [Parameter(Mandatory=$true)][string]$RepoDir,
    [ValidateSet("Machine","User")][string]$InstallScope = "Machine",
    [switch]$UpgradeOnly,
    [switch]$NoDocker,
    [int]$GrafanaPort = 3000,
    [int]$ServicePort = 8000
  )
  return @{
    repo_url = $RepoUrl
    install_root = $InstallRoot
    repo_dir = $RepoDir
    install_scope = $InstallScope
    upgrade_only = [bool]$UpgradeOnly
    no_docker = [bool]$NoDocker
    grafana_port = $GrafanaPort
    service_port = $ServicePort
  }
}

function Get-GadosSteps {
  param(
    [Parameter(Mandatory=$true)]$Desired,
    [Parameter(Mandatory=$true)][string]$ScriptPath
  )

  $resumeBase = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $ScriptPath + '"'
  if ($Desired.no_docker) {
    $resumeBase = $resumeBase + " -NoDocker"
  }

  $steps = @()

  $steps += @{
    id="runtime"
    title="Verify PowerShell runtime"
    test = {
      param($facts)
      if (-not $facts.is_windows) {
        return (New-GadosDecision -Decision "ABORT" -Detected "Not Windows." -Changed "nothing" -Action "Run this installer on Windows." -Resume $resumeBase)
      }
      # WPF UI requires Windows PowerShell 5.1; we allow headless on pwsh.
      return (New-GadosDecision -Decision "SKIP" -Detected ("PowerShell " + $facts.ps_edition + " " + $facts.ps_version) -Changed "nothing" -Action "none" -Resume $resumeBase)
    }
    apply = { param($facts,$log) }
  }

  $steps += @{
    id="admin"
    title="Check privileges"
    test = {
      param($facts)
      if ($Desired.install_scope -eq "User") {
        return (New-GadosDecision -Decision "SKIP" -Detected "Install scope=user (admin not required for filesystem writes)." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      if ($facts.is_admin) {
        return (New-GadosDecision -Decision "SKIP" -Detected "Running as Administrator." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      return (New-GadosDecision -Decision "PAUSE" -Detected "Not running as Administrator." -Changed "nothing" -Action "Open Windows PowerShell as Administrator, then re-run." -Resume $resumeBase)
    }
    apply = { param($facts,$log) }
  }

  $steps += @{
    id="ports"
    title="Check required ports"
    test = {
      param($facts)
      if ($Desired.no_docker) {
        if ($facts.service_port_in_use) {
          return (New-GadosDecision -Decision "PAUSE" -Detected ("Port " + $Desired.service_port + " is in use.") -Changed "nothing" -Action "Stop the process using the port or choose a different port in your environment and retry." -Resume $resumeBase)
        }
        return (New-GadosDecision -Decision "SKIP" -Detected ("Service port " + $Desired.service_port + " is free.") -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      if ($facts.service_port_in_use -or $facts.grafana_port_in_use) {
        $d = @()
        if ($facts.grafana_port_in_use) { $d += ("Grafana port " + $Desired.grafana_port + " is in use") }
        if ($facts.service_port_in_use) { $d += ("Service port " + $Desired.service_port + " is in use") }
        return (New-GadosDecision -Decision "PAUSE" -Detected ($d -join "; ") -Changed "nothing" -Action "Stop the process(es) using the port(s), then re-run." -Resume $resumeBase)
      }
      return (New-GadosDecision -Decision "SKIP" -Detected "Required ports appear free." -Changed "nothing" -Action "none" -Resume $resumeBase)
    }
    apply = { param($facts,$log) }
  }

  $steps += @{
    id="winget"
    title="Check winget availability"
    test = {
      param($facts)
      if ($facts.has_winget) {
        return (New-GadosDecision -Decision "SKIP" -Detected "winget present." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      return (New-GadosDecision -Decision "PAUSE" -Detected "winget not found." -Changed "nothing" -Action "Install 'App Installer' from Microsoft Store (winget), then re-run." -Resume $resumeBase)
    }
    apply = { param($facts,$log) }
  }

  $steps += @{
    id="git"
    title="Ensure Git installed"
    test = {
      param($facts)
      if ($facts.has_git) {
        return (New-GadosDecision -Decision "SKIP" -Detected "Git present." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      return (New-GadosDecision -Decision "APPLY" -Detected "Git missing." -Changed "will install via winget" -Action "none" -Resume $resumeBase)
    }
    apply = {
      param($facts,$log)
      Invoke-GadosCmd -Title "Installing Git via winget..." -Log $log -Fn {
        winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
      }
    }
  }

  $steps += @{
    id="python"
    title="Ensure Python installed"
    test = {
      param($facts)
      if ($facts.has_python) {
        return (New-GadosDecision -Decision "SKIP" -Detected ("Python present: " + $facts.python_version) -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      return (New-GadosDecision -Decision "APPLY" -Detected "Python missing." -Changed "will install via winget" -Action "none" -Resume $resumeBase)
    }
    apply = {
      param($facts,$log)
      Invoke-GadosCmd -Title "Installing Python via winget..." -Log $log -Fn {
        winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements
      }
    }
  }

  if (-not $Desired.no_docker) {
    $steps += @{
      id="docker"
      title="Ensure Docker Desktop installed"
      test = {
        param($facts)
        if ($facts.has_docker) {
          return (New-GadosDecision -Decision "SKIP" -Detected "Docker CLI present." -Changed "nothing" -Action "none" -Resume $resumeBase)
        }
        return (New-GadosDecision -Decision "APPLY" -Detected "Docker CLI missing." -Changed "will install Docker Desktop via winget" -Action "none" -Resume $resumeBase)
      }
      apply = {
        param($facts,$log)
        Invoke-GadosCmd -Title "Installing Docker Desktop via winget..." -Log $log -Fn {
          winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements
        }
      }
    }

    $steps += @{
      id="docker_ready"
      title="Verify Docker engine is running"
      test = {
        param($facts)
        if (-not $facts.has_docker) {
          return (New-GadosDecision -Decision "PAUSE" -Detected "Docker not installed." -Changed "nothing" -Action "Install Docker Desktop, start it, then re-run." -Resume $resumeBase)
        }
        if (-not $facts.has_docker_compose) {
          return (New-GadosDecision -Decision "PAUSE" -Detected "docker compose not available." -Changed "nothing" -Action "Start Docker Desktop and ensure Compose is enabled, then re-run." -Resume $resumeBase)
        }
        if (-not $facts.docker_running) {
          $d = $facts.docker_diag
          $hints = @()
          if ($d.docker_service_running -eq $false) { $hints += "Docker Desktop service not running (com.docker.service)" }
          if ($d.wsl_present -eq $false) { $hints += "WSL not available (wsl.exe missing or not enabled)" }
          if ($d.wsl_feature_enabled -eq $false) { $hints += "Windows feature 'Microsoft-Windows-Subsystem-Linux' is disabled" }
          if ($d.vmp_enabled -eq $false) { $hints += "Windows feature 'VirtualMachinePlatform' is disabled" }
          if ($d.hypervisorlaunchtype -eq "Off") { $hints += "Hypervisor is disabled at boot (hypervisorlaunchtype Off)" }
          $hintText = if ($hints.Count -gt 0) { (" Hints: " + ($hints -join "; ") + ".") } else { "" }
          $action = "Start Docker Desktop. If it still fails: enable WSL2 + Virtual Machine Platform, ensure virtualization is enabled in BIOS, then reboot. Then re-run."
          return (New-GadosDecision -Decision "PAUSE" -Detected ("Docker engine not reachable (docker info failed)." + $hintText) -Changed "nothing" -Action $action -Resume $resumeBase)
        }
        return (New-GadosDecision -Decision "SKIP" -Detected "Docker engine reachable." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      apply = { param($facts,$log) }
    }
  }

  $steps += @{
    id="repo"
    title="Clone or update repo"
    test = {
      param($facts)
      if ($facts.repo_dir_exists) {
        return (New-GadosDecision -Decision "APPLY" -Detected ("Repo present at " + $Desired.repo_dir) -Changed "will refresh to latest main" -Action "none" -Resume $resumeBase)
      }
      return (New-GadosDecision -Decision "APPLY" -Detected "Repo not present." -Changed ("will clone " + $Desired.repo_url) -Action "none" -Resume $resumeBase)
    }
    apply = {
      param($facts,$log)
      New-Item -ItemType Directory -Force -Path $Desired.install_root | Out-Null
      if (!(Test-Path $Desired.repo_dir)) {
        Invoke-GadosCmd -Title ("Cloning repo to " + $Desired.repo_dir + "...") -Log $log -Fn {
          git clone $Desired.repo_url $Desired.repo_dir
        }
        return
      }
      Invoke-GadosCmd -Title "Updating repo (fetch + checkout main + pull)..." -Log $log -Fn {
        Push-Location $Desired.repo_dir
        git fetch --all --prune
        git checkout main 2>$null
        git pull --ff-only
        Pop-Location
      }
    }
  }

  $steps += @{
    id="venv"
    title="Create Python virtualenv + install dependencies"
    test = {
      param($facts)
      if (-not $facts.repo_dir_exists) {
        return (New-GadosDecision -Decision "PAUSE" -Detected "Repo not available yet." -Changed "nothing" -Action "Let the installer complete the repo step, then re-run." -Resume $resumeBase)
      }
      $venvPy = Join-Path $Desired.repo_dir ".venv\Scripts\python.exe"
      if (Test-Path $venvPy) {
        return (New-GadosDecision -Decision "APPLY" -Detected "Virtualenv exists." -Changed "will ensure deps installed/updated" -Action "none" -Resume $resumeBase)
      }
      return (New-GadosDecision -Decision "APPLY" -Detected "Virtualenv missing." -Changed "will create and install deps" -Action "none" -Resume $resumeBase)
    }
    apply = {
      param($facts,$log)
      Push-Location $Desired.repo_dir
      Invoke-GadosCmd -Title "Creating venv (.venv)..." -Log $log -Fn { python -m venv .venv }
      Invoke-GadosCmd -Title "Upgrading pip..." -Log $log -Fn { .\.venv\Scripts\python.exe -m pip install --upgrade pip }
      Invoke-GadosCmd -Title "Installing repo deps (requirements.txt)..." -Log $log -Fn { .\.venv\Scripts\pip.exe install -r requirements.txt }
      # Optional: install control-plane package if present (PR branch adds this).
      if (Test-Path (Join-Path $Desired.repo_dir "gados-control-plane\pyproject.toml")) {
        Invoke-GadosCmd -Title "Installing control-plane package (editable)..." -Log $log -Fn { .\.venv\Scripts\pip.exe install -e gados-control-plane }
      }
      Pop-Location
    }
  }

  if (-not $Desired.no_docker) {
    $steps += @{
      id="compose_up"
      title="Start Docker stack (compose.test.yml preferred)"
      test = {
        param($facts)
        if (-not $facts.has_docker -or -not $facts.docker_running) {
          return (New-GadosDecision -Decision "PAUSE" -Detected "Docker engine not ready." -Changed "nothing" -Action "Start Docker Desktop and retry." -Resume $resumeBase)
        }
        if (-not $facts.repo_dir_exists) {
          return (New-GadosDecision -Decision "PAUSE" -Detected "Repo not available yet." -Changed "nothing" -Action "Let the repo step complete, then re-run." -Resume $resumeBase)
        }
        if ($facts.has_compose_test) {
          return (New-GadosDecision -Decision "APPLY" -Detected "compose.test.yml present." -Changed "will start test stack" -Action "none" -Resume $resumeBase)
        }
        if ($facts.has_compose_obs) {
          return (New-GadosDecision -Decision "APPLY" -Detected "docker-compose.yml present." -Changed "will start observability stack" -Action "none" -Resume $resumeBase)
        }
        return (New-GadosDecision -Decision "SKIP" -Detected "No compose file found; skipping Docker stack." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      apply = {
        param($facts,$log)
        Push-Location $Desired.repo_dir
        if (Test-Path "compose.test.yml") {
          Invoke-GadosCmd -Title "docker compose -f compose.test.yml up -d --build" -Log $log -Fn { docker compose -f compose.test.yml up -d --build }
        } else {
          Invoke-GadosCmd -Title "docker compose up -d" -Log $log -Fn { docker compose up -d }
        }
        Pop-Location
      }
    }

    $steps += @{
      id="smoke_docker"
      title="Docker-mode smoke checks (Grafana + service)"
      test = {
        param($facts)
        if (-not $facts.repo_dir_exists) {
          return (New-GadosDecision -Decision "PAUSE" -Detected "Repo not available yet." -Changed "nothing" -Action "Let the repo step complete, then re-run." -Resume $resumeBase)
        }
        return (New-GadosDecision -Decision "APPLY" -Detected "Will run smoke checks." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      apply = {
        param($facts,$log)
        # Grafana health (best-effort; only valid if stack exposes it)
        $gUrl = ("http://localhost:" + $Desired.grafana_port + "/api/health")
        if (-not (Invoke-GadosHttpWaitOk -Url $gUrl -Retries 60 -SleepMs 1000)) {
          throw ("Grafana health check failed at " + $gUrl)
        }
        Write-GadosLog -Log $log -Message "Detected: Grafana health OK" -Level "INFO"

        # Service health:
        # - If compose.test.yml is used, the service should already be running on :8000.
        # - Else run it temporarily from the venv (no-Docker service smoke).
        $svcUrl = ("http://localhost:" + $Desired.service_port + "/health")
        if (Invoke-GadosHttpWaitOk -Url $svcUrl -Retries 30 -SleepMs 500) {
          Write-GadosLog -Log $log -Message "Detected: Service health OK (existing process)" -Level "INFO"
          return
        }
        # Fall back to local process smoke (OTEL disabled).
        Push-Location $Desired.repo_dir
        $env:OTEL_SDK_DISABLED = "true"
        $p = Start-Process -PassThru -WindowStyle Hidden -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$Desired.service_port.ToString())
        try {
          if (-not (Invoke-GadosHttpWaitOk -Url $svcUrl -Retries 30 -SleepMs 500)) {
            throw ("Service health check failed at " + $svcUrl)
          }
          Invoke-RestMethod -TimeoutSec 5 -Method Post -Uri ("http://localhost:" + $Desired.service_port + "/track") -ContentType "application/json" -Body '{"event":"win_smoke","user_id":"local","properties":{"source":"installer"}}' | Out-Null
          Write-GadosLog -Log $log -Message "Detected: Service /track OK" -Level "INFO"
        } finally {
          try { if (!$p.HasExited) { Stop-Process -Id $p.Id -Force } } catch {}
          Pop-Location
        }
      }
    }
  } else {
    $steps += @{
      id="smoke_nodocker"
      title="No-Docker smoke checks (service only)"
      test = {
        param($facts)
        return (New-GadosDecision -Decision "APPLY" -Detected "NoDocker=true (skipping Grafana/LGTM)." -Changed "nothing" -Action "none" -Resume $resumeBase)
      }
      apply = {
        param($facts,$log)
        Push-Location $Desired.repo_dir
        $env:OTEL_SDK_DISABLED = "true"
        $svcUrl = ("http://localhost:" + $Desired.service_port + "/health")
        $p = Start-Process -PassThru -WindowStyle Hidden -FilePath ".\.venv\Scripts\python.exe" -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port",$Desired.service_port.ToString())
        try {
          if (-not (Invoke-GadosHttpWaitOk -Url $svcUrl -Retries 30 -SleepMs 500)) {
            throw ("Service health check failed at " + $svcUrl)
          }
          Invoke-RestMethod -TimeoutSec 5 -Method Post -Uri ("http://localhost:" + $Desired.service_port + "/track") -ContentType "application/json" -Body '{"event":"win_smoke","user_id":"local","properties":{"source":"installer"}}' | Out-Null
          Write-GadosLog -Log $log -Message "Detected: Service /track OK" -Level "INFO"
        } finally {
          try { if (!$p.HasExited) { Stop-Process -Id $p.Id -Force } } catch {}
          Pop-Location
        }
      }
    }
  }

  return $steps
}

function Invoke-GadosInstallerController {
  param(
    [Parameter(Mandatory=$true)]$Desired,
    [Parameter(Mandatory=$true)][string]$StatePath,
    [Parameter(Mandatory=$true)]$Log,
    [Parameter(Mandatory=$true)][string]$ScriptPath,
    [switch]$Reset
  )

  if ($Reset) {
    Write-GadosLog -Log $Log -Message "Reset requested: deleting state/log." -Level "WARN"
    try { if (Test-Path $StatePath) { Remove-Item -Force $StatePath } } catch {}
    try { if (Test-Path $Log.path) { Remove-Item -Force $Log.path } } catch {}
  }

  $state = Read-GadosInstallerState -StatePath $StatePath
  $state.last_run = @{
    started_at_utc = (Get-Date).ToUniversalTime().ToString("s") + "Z"
    desired = $Desired
  }
  $state.blocked = $null

  $facts = Get-GadosFacts -RepoDir $Desired.repo_dir -GrafanaPort $Desired.grafana_port -ServicePort $Desired.service_port
  $steps = Get-GadosSteps -Desired $Desired -ScriptPath $ScriptPath

  foreach ($s in $steps) {
    $id = $s.id
    $title = $s.title
    Write-GadosLog -Log $Log -Message ("Evaluating: " + $title) -Level "INFO"

    $decision = & $s.test $facts

    $resume = $decision.resume
    $calm = @(
      ("Detected: " + $decision.detected),
      ("Changed:  " + $decision.changed),
      ("Action:   " + $decision.action),
      ("Resume:   " + $resume)
    )
    foreach ($line in $calm) { Write-GadosLog -Log $Log -Message $line -Level "INFO" }

    if ($decision.decision -eq "SKIP") {
      $sr = New-GadosStepResult -Id $id -Title $title -Status "SKIPPED" -DecisionObj $decision
      Set-GadosStepState -State $state -StepResult $sr
      continue
    }

    if ($decision.decision -eq "PAUSE") {
      $sr = New-GadosStepResult -Id $id -Title $title -Status "PAUSED" -DecisionObj $decision -Note $decision.action
      Set-GadosStepState -State $state -StepResult $sr
      $state.blocked = @{
        step_id = $id
        title = $title
        calm = $decision
      }
      Write-GadosInstallerState -State $state -StatePath $StatePath
      throw ("Blocked: " + $title + " — " + $decision.action)
    }

    if ($decision.decision -eq "ABORT") {
      $sr = New-GadosStepResult -Id $id -Title $title -Status "ABORTED" -DecisionObj $decision -Note $decision.action
      Set-GadosStepState -State $state -StepResult $sr
      $state.blocked = @{
        step_id = $id
        title = $title
        calm = $decision
      }
      Write-GadosInstallerState -State $state -StatePath $StatePath
      throw ("Aborted: " + $title + " — " + $decision.action)
    }

    # APPLY
    $srRun = New-GadosStepResult -Id $id -Title $title -Status "RUNNING" -DecisionObj $decision
    Set-GadosStepState -State $state -StepResult $srRun
    Write-GadosInstallerState -State $state -StatePath $StatePath

    try {
      & $s.apply $facts $Log
      $srOk = New-GadosStepResult -Id $id -Title $title -Status "DONE" -DecisionObj $decision
      Set-GadosStepState -State $state -StepResult $srOk
      # Re-observe reality after each APPLY (controller loop).
      $facts = Get-GadosFacts -RepoDir $Desired.repo_dir -GrafanaPort $Desired.grafana_port -ServicePort $Desired.service_port
    } catch {
      $msg = $_.Exception.Message
      $srFail = New-GadosStepResult -Id $id -Title $title -Status "FAILED" -DecisionObj $decision -Note $msg
      Set-GadosStepState -State $state -StepResult $srFail
      $state.blocked = @{
        step_id = $id
        title = $title
        calm = (New-GadosDecision -Decision "PAUSE" -Detected $decision.detected -Changed "nothing" -Action $msg -Resume $decision.resume)
      }
      Write-GadosInstallerState -State $state -StatePath $StatePath
      Write-GadosLog -Log $Log -Message ("FAILED: " + $title + " :: " + $msg) -Level "ERROR"
      throw
    }
  }

  Write-GadosInstallerState -State $state -StatePath $StatePath
  Write-GadosLog -Log $Log -Message "Install complete." -Level "INFO"
  return $state
}

Export-ModuleMember -Function `
  Read-GadosInstallerState, `
  Write-GadosInstallerState, `
  New-GadosLog, `
  Write-GadosLog, `
  Get-GadosDesiredState, `
  Get-GadosFacts, `
  Invoke-GadosInstallerController

