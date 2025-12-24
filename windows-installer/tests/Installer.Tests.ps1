Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Describe "GADOS Windows installer decision engine" {
  BeforeAll {
    $here = Split-Path -Parent $PSCommandPath
    $mod = Join-Path (Split-Path -Parent $here) "GadosInstaller.psm1"
    Import-Module $mod -Force
  }

  It "computes desired state with NoDocker" {
    $d = Get-GadosDesiredState -RepoUrl "https://example.com/repo" -InstallRoot "C:\X" -RepoDir "C:\X\repo" -NoDocker
    $d.no_docker | Should -BeTrue
  }

  It "creates state when missing" {
    $tmp = Join-Path $env:TEMP ("gados_state_" + [guid]::NewGuid().ToString() + ".json")
    try {
      $s = Read-GadosInstallerState -StatePath $tmp
      $s.schema | Should -Be "gados.windows.installer.state.v2"
      $s.steps.Keys.Count | Should -Be 0
    } finally {
      try { Remove-Item -Force $tmp } catch {}
    }
  }

  It "detects docker facts when docker is missing (no throw)" {
    # On machines without docker, Get-GadosFacts should not throw.
    $f = Get-GadosFacts -RepoDir "C:\does-not-exist"
    $f | Should -Not -BeNullOrEmpty
  }
}

