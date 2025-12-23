## Windows installer (resumable, UI)

This folder contains a Windows-first install utility for GADOS that:

- runs **step-by-step** with a **GUI** (progress + live logs)
- supports **resume** after failure/reboot (persists state under ProgramData)
- supports **fresh install** and **upgrade**
- performs **post-install observability checks** (Grafana + service health + smoke)

### What it installs/configures (default path)

- Git (if missing) via `winget` (preferred) or prompts user
- Python 3.x (if missing) via `winget`
- Docker Desktop (if missing) via `winget`
- Clones/updates this repo into `C:\ProgramData\GADOS\repo`
- Starts the local LGTM stack via `docker compose up -d`
- Runs smoke checks:
  - `http://localhost:3000/api/health` (Grafana)
  - `http://localhost:8000/health` (service, started temporarily)

### Run

Open **Windows PowerShell** as Administrator and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\windows-installer\install.ps1
```

### Notes

- This script targets **Windows PowerShell 5.1** for WPF UI compatibility.
- If you want headless mode:

```powershell
.\windows-installer\install.ps1 -NoUI
```

