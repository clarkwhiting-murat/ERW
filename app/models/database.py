from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Support both PostgreSQL (Docker) and SQLite (standalone)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    None  # Will default based on environment
)

# Auto-detect: Use SQLite if DATABASE_URL not set (standalone mode)
# Use PostgreSQL if DATABASE_URL is set (Docker mode)
if DATABASE_URL is None:
    # Standalone mode - use SQLite
    DATABASE_URL = "sqlite:///./mining_db.sqlite"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # SQLite-specific
        echo=False
    )
elif DATABASE_URL.startswith("sqlite"):
    # Explicit SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # PostgreSQL (Docker) with connection pooling
    engine = create_engine(
        DATABASE_URL,
        echo=False,  # Set to False for production
        pool_size=5,  # Number of connections to keep open
        max_overflow=10,  # Max connections beyond pool_size
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600  # Recycle connections after 1 hour
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

