# Building Windows Executable via GitHub Actions

## Overview

The application now supports both:
- **Docker (Mac/Linux)**: Uses PostgreSQL database
- **Windows .exe**: Uses SQLite database (standalone)

## How to Build Windows .exe

### Step 1: Push to GitHub

Make sure your code is pushed to a GitHub repository.

### Step 2: Trigger GitHub Actions

1. Go to your GitHub repository
2. Click on the **"Actions"** tab
3. Select **"Build Windows Executable"** workflow
4. Click **"Run workflow"** button
5. Click the green **"Run workflow"** button again

### Step 3: Download the Executable

1. Wait for the workflow to complete (takes ~5-10 minutes)
2. Once complete, click on the workflow run
3. Scroll down to **"Artifacts"** section
4. Download **"CO2_Retention_Simulator-Windows"**
5. Extract the zip file to get `CO2_Retention_Simulator.exe`

## How It Works

### Docker Mode (Mac/Linux)
- `docker-compose.yml` sets `DATABASE_URL` environment variable
- Application detects PostgreSQL connection string
- Uses PostgreSQL database

### Standalone Mode (Windows .exe)
- No `DATABASE_URL` environment variable set
- Application auto-detects and uses SQLite
- Creates `mining_db.sqlite` file in the same directory as the .exe

## File Changes Made

1. **`app/models/database.py`**: Auto-detects database type (PostgreSQL vs SQLite)
2. **`app/main.py`**: Handles both Docker and PyInstaller file paths
3. **`start_embedded.py`**: Entry point for Windows .exe
4. **`.github/workflows/build-windows.yml`**: GitHub Actions workflow

## Testing

### Test Docker (Mac):
```bash
docker-compose up
```
Should use PostgreSQL (check logs for connection string)

### Test Standalone (after building .exe):
- Double-click `CO2_Retention_Simulator.exe`
- Should create `mining_db.sqlite` file
- Should open browser at http://localhost:8000

## Notes

- The .exe file will be large (~50-100MB) as it includes Python and all dependencies
- SQLite database file (`mining_db.sqlite`) is created automatically in the same directory as the .exe
- Users can delete `mining_db.sqlite` to reset the database
- The .exe is self-contained - no Python installation needed on Windows

