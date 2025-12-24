## Windows installer (resumable, UI)

This folder contains a Windows-first install utility for GADOS that:

- runs **step-by-step** with a **GUI** (progress + live logs)
- supports **resume** after failure/reboot (persists state under ProgramData / LocalAppData)
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
.\windows-installer\install.cmd
```

### Notes

- Use `install.cmd` to avoid running the script under the wrong interpreter (common cause of `CmdletBinding/param` parse errors).
- The UI targets **Windows PowerShell 5.1** for WPF compatibility.
- If you want headless mode:

```powershell
.\windows-installer\install.ps1 -NoUI
```

### No-Docker mode (recommended for constrained environments)

If Docker Desktop is blocked/unreliable, you can still install and run smoke checks for the service:

```powershell
.\windows-installer\install.ps1 -NoUI -NoDocker
```

