"""
Entry point for standalone Windows executable.
This file is used by PyInstaller to create the .exe
"""
import os
import sys
import webbrowser
import threading
import time
from pathlib import Path

# Set SQLite as default database for standalone mode
# (Docker will override this via DATABASE_URL env var)
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///./mining_db.sqlite"

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)
    try:
        webbrowser.open('http://localhost:8000/ui')
    except Exception:
        pass  # Browser opening is optional

if __name__ == '__main__':
    # Open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Import and run the app
    import uvicorn
    from app.main import app
    
    print("=" * 50)
    print("CO₂ Retention Simulator")
    print("=" * 50)
    print("\nServer starting at http://localhost:8000")
    print("Web UI available at http://localhost:8000/ui")
    print("Browser will open automatically...")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Run the server
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8000,
        log_level='info'
    )

