param(
  [switch]$NoUI,
  [switch]$Reset,
  [switch]$UpgradeOnly,
  [string]$RepoUrl = "https://github.com/gaI-observe-online/devagents",
  [string]$InstallRoot = "C:\ProgramData\GADOS",
  [string]$RepoDir = "C:\ProgramData\GADOS\repo"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ----------------------------
# State + logging
# ----------------------------

$StateDir = Join-Path $InstallRoot "installer"
$StatePath = Join-Path $StateDir "state.json"
$LogPath = Join-Path $StateDir "install.log"

function Ensure-Dirs {
  New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
}

function Write-Log([string]$Message, [string]$Level = "INFO") {
  Ensure-Dirs
  $ts = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  $line = "$ts [$Level] $Message"
  Add-Content -Path $LogPath -Value $line -Encoding UTF8
  if ($script:UiLogAppend) { $script:UiLogAppend.Invoke($line) }
}

function Load-State {
  Ensure-Dirs
  if (!(Test-Path $StatePath)) {
    return @{
      schema = "gados.windows.installer.state.v1"
      created_at = (Get-Date).ToUniversalTime().ToString("s") + "Z"
      last_updated_at = (Get-Date).ToUniversalTime().ToString("s") + "Z"
      current_step = 0
      steps = @{}
    }
  }
  return (Get-Content $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable)
}

function Save-State($state) {
  Ensure-Dirs
  $state.last_updated_at = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  ($state | ConvertTo-Json -Depth 10) | Set-Content -Path $StatePath -Encoding UTF8
}

function Set-StepStatus($state, [string]$id, [string]$status, [string]$note = "") {
  if (-not $state.steps.ContainsKey($id)) { $state.steps[$id] = @{} }
  $state.steps[$id].status = $status  # PENDING|RUNNING|DONE|FAILED|SKIPPED
  $state.steps[$id].note = $note
  $state.steps[$id].updated_at = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  Save-State $state
}

function Require-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Administrator privileges required. Re-run PowerShell as Administrator."
  }
}

function Has-Cmd([string]$name) {
  return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Run([string]$title, [scriptblock]$fn) {
  Write-Log $title "INFO"
  & $fn
}

# ----------------------------
# Steps
# ----------------------------

$Steps = @(
  @{ id="admin"; title="Check Administrator privileges"; run={ Require-Admin } },
  @{ id="winget"; title="Check winget availability"; run={
      if (-not (Has-Cmd "winget")) {
        throw "winget not found. Install 'App Installer' from Microsoft Store or use a Windows image with winget."
      }
    }
  },
  @{ id="git"; title="Install Git if missing"; run={
      if (Has-Cmd "git") { Write-Log "Git present" "INFO"; return }
      Run "Installing Git via winget..." { winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements }
    }
  },
  @{ id="python"; title="Install Python if missing"; run={
      if (Has-Cmd "python") { Write-Log "Python present" "INFO"; return }
      Run "Installing Python via winget..." { winget install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements }
    }
  },
  @{ id="docker"; title="Install Docker Desktop if missing"; run={
      if (Has-Cmd "docker") { Write-Log "Docker CLI present" "INFO"; return }
      Run "Installing Docker Desktop via winget..." { winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements }
      Write-Log "Docker Desktop installed. You may need to log out/in or reboot. Resume installer afterwards." "WARN"
    }
  },
  @{ id="repo"; title="Clone or update repo"; run={
      Ensure-Dirs
      New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
      if (!(Test-Path $RepoDir)) {
        Run "Cloning repo to $RepoDir..." { git clone $RepoUrl $RepoDir }
      } else {
        if ($UpgradeOnly -or $true) {
          Run "Updating repo (git fetch + reset)..." {
            Push-Location $RepoDir
            git fetch --all --prune
            # Prefer main, but allow detached / local workflow.
            git checkout main 2>$null
            git pull --ff-only
            Pop-Location
          }
        }
      }
    }
  },
  @{ id="compose_up"; title="Start observability stack (docker compose)"; run={
      if (-not (Has-Cmd "docker")) { throw "docker not found. Start Docker Desktop and resume." }
      Push-Location $RepoDir
      Run "docker compose up -d" { docker compose up -d }
      Pop-Location
    }
  },
  @{ id="smoke"; title="Run smoke checks (Grafana + service)"; run={
      Push-Location $RepoDir

      # Grafana health
      Run "Checking Grafana health..." {
        $ok = $false
        for ($i=0; $i -lt 60; $i++) {
          try {
            $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri "http://localhost:3000/api/health"
            if ($r.StatusCode -eq 200) { $ok = $true; break }
          } catch {}
          Start-Sleep -Seconds 1
        }
        if (-not $ok) { throw "Grafana health check failed at http://localhost:3000/api/health" }
        Write-Log "Grafana health OK" "INFO"
      }

      # Service smoke (start temporarily)
      Run "Starting service for smoke..." {
        $env:OTEL_SDK_DISABLED = "true"
        $p = Start-Process -PassThru -WindowStyle Hidden -FilePath "python" -ArgumentList @("-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000")
        Start-Sleep -Seconds 1
        $ok = $false
        for ($i=0; $i -lt 30; $i++) {
          try {
            $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri "http://localhost:8000/health"
            if ($r.StatusCode -eq 200) { $ok = $true; break }
          } catch {}
          Start-Sleep -Milliseconds 500
        }
        try {
          if (-not $ok) { throw "Service health check failed at http://localhost:8000/health" }
          Write-Log "Service health OK" "INFO"
          # Trigger one analytics event
          Invoke-RestMethod -TimeoutSec 5 -Method Post -Uri "http://localhost:8000/track" -ContentType "application/json" -Body '{"event":"win_smoke","user_id":"local","properties":{"source":"installer"}}' | Out-Null
          Write-Log "Service /track OK" "INFO"
        } finally {
          if (!$p.HasExited) { Stop-Process -Id $p.Id -Force }
        }
      }

      Pop-Location
    }
  }
)

function Run-Steps {
  $state = Load-State
  if ($Reset) {
    Write-Log "Reset requested: deleting state/log." "WARN"
    if (Test-Path $StatePath) { Remove-Item -Force $StatePath }
    if (Test-Path $LogPath) { Remove-Item -Force $LogPath }
    $state = Load-State
  }

  $startIdx = [int]$state.current_step
  for ($i=$startIdx; $i -lt $Steps.Count; $i++) {
    $step = $Steps[$i]
    $state.current_step = $i
    Save-State $state

    Set-StepStatus $state $step.id "RUNNING"
    try {
      Write-Log ("STEP " + ($i+1) + "/" + $Steps.Count + ": " + $step.title) "INFO"
      & $step.run
      Set-StepStatus $state $step.id "DONE"
    } catch {
      $msg = $_.Exception.Message
      Set-StepStatus $state $step.id "FAILED" $msg
      Write-Log ("FAILED: " + $step.title + " :: " + $msg) "ERROR"
      throw
    } finally {
      $state.current_step = $i + 1
      Save-State $state
      if ($script:UiProgressUpdate) { $script:UiProgressUpdate.Invoke($i+1, $Steps.Count) }
      if ($script:UiStepUpdate) { $script:UiStepUpdate.Invoke($state) }
    }
  }

  Write-Log "Install complete." "INFO"
}

# ----------------------------
# UI (WPF)
# ----------------------------

function Start-UI {
  Add-Type -AssemblyName PresentationFramework

  $xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="GADOS Installer" Height="620" Width="900" WindowStartupLocation="CenterScreen">
  <Grid Margin="12">
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="Auto"/>
    </Grid.RowDefinitions>

    <StackPanel Grid.Row="0" Orientation="Vertical">
      <TextBlock FontSize="18" FontWeight="Bold" Text="GADOS Windows Installer"/>
      <TextBlock Margin="0,4,0,0" Text="Resumable step-by-step install with smoke checks."/>
    </StackPanel>

    <Grid Grid.Row="1" Margin="0,12,0,12">
      <Grid.ColumnDefinitions>
        <ColumnDefinition Width="320"/>
        <ColumnDefinition Width="*"/>
      </Grid.ColumnDefinitions>

      <GroupBox Header="Steps" Grid.Column="0" Margin="0,0,12,0">
        <ScrollViewer VerticalScrollBarVisibility="Auto">
          <StackPanel Name="StepsPanel" Margin="8"/>
        </ScrollViewer>
      </GroupBox>

      <GroupBox Header="Log" Grid.Column="1">
        <TextBox Name="LogBox" Margin="8" IsReadOnly="True" TextWrapping="NoWrap"
                 VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Auto"/>
      </GroupBox>
    </Grid>

    <StackPanel Grid.Row="2" Orientation="Vertical">
      <ProgressBar Name="Progress" Height="18" Minimum="0" Maximum="100"/>
      <StackPanel Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,10,0,0">
        <Button Name="BtnStart" Width="120" Height="34" Margin="0,0,8,0" Content="Start / Resume"/>
        <Button Name="BtnReset" Width="120" Height="34" Margin="0,0,8,0" Content="Reset"/>
        <Button Name="BtnExit" Width="120" Height="34" Content="Exit"/>
      </StackPanel>
    </StackPanel>
  </Grid>
</Window>
"@

  $reader = (New-Object System.Xml.XmlNodeReader ([xml]$xaml))
  $win = [Windows.Markup.XamlReader]::Load($reader)

  $stepsPanel = $win.FindName("StepsPanel")
  $logBox = $win.FindName("LogBox")
  $progress = $win.FindName("Progress")
  $btnStart = $win.FindName("BtnStart")
  $btnReset = $win.FindName("BtnReset")
  $btnExit = $win.FindName("BtnExit")

  function Render-Steps($state) {
    $stepsPanel.Children.Clear()
    foreach ($s in $Steps) {
      $status = "PENDING"
      $note = ""
      if ($state.steps.ContainsKey($s.id)) {
        $status = $state.steps[$s.id].status
        $note = $state.steps[$s.id].note
      }
      $suffix = ""
      if ($note) { $suffix = " - $note" }
      $tb = New-Object System.Windows.Controls.TextBlock
      $tb.Text = "[$status] $($s.title)$suffix"
      $tb.Margin = "0,0,0,6"
      $stepsPanel.Children.Add($tb) | Out-Null
    }
  }

  $script:UiLogAppend = {
    param($line)
    $win.Dispatcher.Invoke([action]{
      $logBox.AppendText($line + "`r`n")
      $logBox.ScrollToEnd()
    }) | Out-Null
  }

  $script:UiProgressUpdate = {
    param($done, $total)
    $pct = [int](($done / [double]$total) * 100)
    $win.Dispatcher.Invoke([action]{ $progress.Value = $pct }) | Out-Null
  }

  $script:UiStepUpdate = {
    param($state)
    $win.Dispatcher.Invoke([action]{ Render-Steps $state }) | Out-Null
  }

  # Initial render
  Render-Steps (Load-State)
  if (Test-Path $LogPath) {
    $logBox.Text = (Get-Content $LogPath -Encoding UTF8 -ErrorAction SilentlyContinue | Out-String)
    $logBox.ScrollToEnd()
  }

  $btnExit.Add_Click({ $win.Close() })
  $btnReset.Add_Click({
    $script:Reset = $true
    try {
      Run-Steps
    } catch {
      [System.Windows.MessageBox]::Show($_.Exception.Message, "Install failed")
    }
  })
  $btnStart.Add_Click({
    try {
      Run-Steps
      [System.Windows.MessageBox]::Show("Install completed successfully.", "GADOS Installer")
    } catch {
      [System.Windows.MessageBox]::Show($_.Exception.Message, "Install failed")
    }
  })

  $win.ShowDialog() | Out-Null
}

try {
  if ($NoUI) {
    Run-Steps
  } else {
    Start-UI
  }
} catch {
  Write-Log $_.Exception.Message "ERROR"
  throw
}

