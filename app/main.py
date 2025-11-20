from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, RedirectResponse
from app.routes import config_routes, lab_data_routes, field_data_routes, model_routes, simulate_routes, results
from app.models.database import engine, Base
# Import all models to ensure they are registered with SQLAlchemy
from app.models import (
    Deposit,
    Configuration,
    LabRecord,
    FieldRecord,
    RiskProfile,
    StatePosterior,
    SimulationResult,
)
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_id import RequestIDMiddleware
import os
import sys
import logging
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Determine base path - handles both Docker and PyInstaller
def get_base_path():
    """Get the base path for the application"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller)
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        # Running as script (Docker or development)
        base_path = Path(__file__).parent.parent
    
    return base_path

BASE_PATH = get_base_path()
STATIC_PATH = BASE_PATH / "static"

# Cache UI index.html path at startup (prevents recurring path resolution issues)
UI_INDEX_PATH = None
if STATIC_PATH.exists():
    index_path = STATIC_PATH / "index.html"
    if index_path.exists():
        UI_INDEX_PATH = str(index_path.resolve())
    else:
        # Try alternative paths at startup
        script_dir = Path(__file__).parent.parent
        alt_paths = [
            script_dir / "static" / "index.html",
            BASE_PATH / "static" / "index.html",
            Path.cwd() / "static" / "index.html",
        ]
        for alt_path in alt_paths:
            try:
                abs_alt = alt_path.resolve() if not alt_path.is_absolute() else alt_path
                if abs_alt.exists() and abs_alt.is_file():
                    UI_INDEX_PATH = str(abs_alt)
                    break
            except Exception:
                continue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log') if not os.getenv("DOCKER_ENV") else logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log path information at startup for debugging
logger.info(f"Application starting - BASE_PATH: {BASE_PATH}, STATIC_PATH: {STATIC_PATH}")
logger.info(f"STATIC_PATH exists: {STATIC_PATH.exists()}")
if UI_INDEX_PATH:
    logger.info(f"✓ UI index.html cached at: {UI_INDEX_PATH}")
else:
    logger.warning("⚠ UI index.html not found at startup - will use fallback redirect")
logger.info(f"Current working directory: {Path.cwd()}")

# Create database tables
Base.metadata.create_all(bind=engine)
logger.info("Database tables created/verified")

app = FastAPI(
    title="Mining API",
    description="FastAPI backend for Mining application",
    version="1.0.0"
)

# Rate limiting - initialize limiter state
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request ID middleware (add first for tracking all requests)
app.add_middleware(RequestIDMiddleware)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# GZip compression middleware (compress responses > 1000 bytes)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware - configurable via environment variable
allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")
if "*" in allowed_origins:
    logger.warning("CORS is allowing all origins. Consider restricting in production.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Mount static files directory (must be before other routes)
# Handle both Docker and PyInstaller scenarios
try:
    if STATIC_PATH.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")
    else:
        # Fallback to relative path (for Docker)
        app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    # If static directory doesn't exist, continue without it
    logger.warning(f"Could not mount static files: {e}")
    pass


# Define specific routes BEFORE parameterized routes to avoid conflicts
@app.get("/")
async def root():
    """Redirect root to UI for better UX"""
    return RedirectResponse(url="/ui")


@app.get("/ui")
async def ui():
    """Serve the web UI - uses cached path from startup for reliability"""
    # Use cached path if available (most efficient and reliable)
    if UI_INDEX_PATH and Path(UI_INDEX_PATH).exists():
        return FileResponse(UI_INDEX_PATH, media_type="text/html")
    
    # Fallback: redirect to static mount (always works if static mount is configured)
    # This is the most reliable fallback since the static mount is set up at startup
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/technical-documentation")
async def technical_documentation():
    """Serve the technical documentation markdown file"""
    # Try multiple path resolution strategies in order of preference
    # Most reliable: relative to this file's location
    script_dir = Path(__file__).parent.parent
    
    possible_paths = [
        script_dir / "docs" / "TECHNICAL_DOCUMENTATION.md",  # Most reliable - relative to script
        BASE_PATH / "docs" / "TECHNICAL_DOCUMENTATION.md",   # BASE_PATH (handles PyInstaller)
        Path.cwd() / "docs" / "TECHNICAL_DOCUMENTATION.md",  # Current working directory
        Path("docs/TECHNICAL_DOCUMENTATION.md"),              # Simple relative
        BASE_PATH / "TECHNICAL_DOCUMENTATION.md",            # Fallback
        Path("TECHNICAL_DOCUMENTATION.md"),                   # Fallback
    ]
    
    logger.info(f"Looking for technical documentation. BASE_PATH: {BASE_PATH}, CWD: {Path.cwd()}")
    
    for doc_path in possible_paths:
        try:
            # Resolve to absolute path - try multiple strategies
            abs_path = None
            
            # Strategy 1: If already absolute, use as-is
            if doc_path.is_absolute():
                abs_path = doc_path
            else:
                # Strategy 2: Try relative to current working directory
                try:
                    test_path = (Path.cwd() / doc_path).resolve()
                    if test_path.exists():
                        abs_path = test_path
                except:
                    pass
                
                # Strategy 3: Try relative to BASE_PATH
                if not abs_path or (abs_path and not abs_path.exists()):
                    try:
                        test_path = (BASE_PATH / doc_path).resolve()
                        if test_path.exists():
                            abs_path = test_path
                    except:
                        pass
                
                # Strategy 4: Try direct resolve
                if not abs_path or (abs_path and not abs_path.exists()):
                    try:
                        abs_path = doc_path.resolve()
                    except:
                        abs_path = Path.cwd() / doc_path
            
            if abs_path:
                logger.info(f"Checking: {abs_path} (exists: {abs_path.exists()}, is_file: {abs_path.is_file() if abs_path.exists() else False})")
            
            if abs_path and abs_path.exists() and abs_path.is_file():
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if content and content.strip():
                        logger.info(f"✓ Successfully loaded from {abs_path} ({len(content)} chars)")
                        # Return as plain text with proper encoding
                        return Response(
                            content=content, 
                            media_type="text/plain; charset=utf-8",
                            headers={"Content-Type": "text/plain; charset=utf-8"}
                        )
                    else:
                        logger.warning(f"File at {abs_path} is empty")
                except UnicodeDecodeError as e:
                    logger.error(f"Encoding error reading {abs_path}: {e}", exc_info=True)
                    # Try with different encoding
                    try:
                        with open(abs_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                        if content and content.strip():
                            logger.info(f"✓ Successfully loaded from {abs_path} with latin-1 encoding ({len(content)} chars)")
                            return Response(content=content, media_type="text/plain; charset=utf-8")
                    except Exception as e2:
                        logger.error(f"Error reading with latin-1: {e2}", exc_info=True)
                        continue
                except Exception as e:
                    logger.error(f"Error reading {abs_path}: {e}", exc_info=True)
                    continue
        except Exception as e:
            logger.debug(f"Error with path {doc_path}: {e}")
            continue
    
    # File not found after trying all paths
    checked = [str(p.resolve() if p.exists() else p) for p in possible_paths[:3]]
    logger.error(f"✗ Technical documentation not found. Checked: {checked}")
    raise HTTPException(status_code=404, detail="Technical documentation not found")


# Include new routes with proper prefixes
# Note: These are included AFTER specific routes like /ui to avoid route conflicts
app.include_router(config_routes.router, prefix="/config", tags=["config"])
app.include_router(lab_data_routes.router, prefix="/lab-data", tags=["lab-data"])
app.include_router(field_data_routes.router, prefix="/field-data", tags=["field-data"])
app.include_router(model_routes.router, prefix="/model", tags=["model"])
app.include_router(simulate_routes.router, prefix="/simulate", tags=["simulate"])
app.include_router(results.router, prefix="/results", tags=["results"])

