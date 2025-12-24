param(
  [switch]$NoUI,
  [switch]$Reset,
  [switch]$UpgradeOnly,
  [switch]$NoDocker,
  [ValidateSet("Machine","User")][string]$InstallScope = "Machine",
  [string]$RepoUrl = "https://github.com/gaI-observe-online/devagents",
  [string]$InstallRoot = "C:\ProgramData\GADOS",
  [string]$RepoDir = "C:\ProgramData\GADOS\repo"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Controller-style installer lives in a module so we can regression-test the decision engine.
$ModulePath = Join-Path $PSScriptRoot "GadosInstaller.psm1"
Import-Module $ModulePath -Force

if ($InstallScope -eq "User" -and $InstallRoot -eq "C:\ProgramData\GADOS") {
  $InstallRoot = Join-Path $env:LOCALAPPDATA "GADOS"
  $RepoDir = Join-Path $InstallRoot "repo"
}

$StateDir = Join-Path $InstallRoot "installer"
$StatePath = Join-Path $StateDir "state.json"
$LogPath = Join-Path $StateDir "install.log"

function Run-Controller {
  $log = New-GadosLog -LogPath $LogPath -UiLogAppend $script:UiLogAppend
  $desired = Get-GadosDesiredState -RepoUrl $RepoUrl -InstallRoot $InstallRoot -RepoDir $RepoDir -InstallScope $InstallScope -UpgradeOnly:$UpgradeOnly -NoDocker:$NoDocker
  return Invoke-GadosInstallerController -Desired $desired -StatePath $StatePath -Log $log -ScriptPath $PSCommandPath -Reset:$Reset
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
    # Steps are computed inside the controller; render a stable view based on state.
    $stepKeys = @()
    if ($state.steps) { $stepKeys = $state.steps.Keys }
    foreach ($k in $stepKeys) {
      $status = "PENDING"
      $note = ""
      $s = $state.steps[$k]
      $status = $s.status
      $note = $s.note
      $tb = New-Object System.Windows.Controls.TextBlock
      $title = $s.title
      $tb.Text = ("[" + $status + "] " + $title + ($(if ($note) { " — " + $note } else { "" })))
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

  # Initial render
  Render-Steps (Read-GadosInstallerState -StatePath $StatePath)
  if (Test-Path $LogPath) {
    $logBox.Text = (Get-Content $LogPath -Encoding UTF8 -ErrorAction SilentlyContinue | Out-String)
    $logBox.ScrollToEnd()
  }

  $btnExit.Add_Click({ $win.Close() })
  $btnReset.Add_Click({
    try {
      $script:Reset = $true
      Run-Controller | Out-Null
      Render-Steps (Read-GadosInstallerState -StatePath $StatePath)
    } catch {
      [System.Windows.MessageBox]::Show($_.Exception.Message, "Install failed")
    }
  })
  $btnStart.Add_Click({
    try {
      Run-Controller | Out-Null
      Render-Steps (Read-GadosInstallerState -StatePath $StatePath)
      [System.Windows.MessageBox]::Show("Install completed successfully.", "GADOS Installer")
    } catch {
      [System.Windows.MessageBox]::Show($_.Exception.Message, "Install failed")
    }
  })

  $win.ShowDialog() | Out-Null
}

try {
  if ($NoUI) {
    Run-Controller | Out-Null
  } else {
    Start-UI
  }
} catch {
  # Best-effort log (module handles file creation).
  try {
    $log = New-GadosLog -LogPath $LogPath -UiLogAppend $null
    Write-GadosLog -Log $log -Message $_.Exception.Message -Level "ERROR"
  } catch {}
  throw
}

