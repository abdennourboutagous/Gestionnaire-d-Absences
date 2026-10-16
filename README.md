# Gestionnaire d'Absences

## Build on Windows 11

Open PowerShell in the project folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The script installs the Python dependencies, downloads the Playwright Chromium browser, and runs PyInstaller. The result is created here:

```text
dist\GestionnaireAbsences\
```