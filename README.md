# Gestionnaire d'Absences

## Build on Windows 11

Requirements:

Open PowerShell in the project folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The script installs the Python dependencies, downloads the Playwright Chromium browser, and runs PyInstaller. The result is created here:

```text
dist\GestionnaireAbsences\
```

## Source mode

To run without PyInstaller:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```