"""
Database Initialization
========================
Create all tables and run migrations
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect
from app.db.models import Base
from app.core.config import settings


def init_db():
    """Initialize database by creating all tables."""
    print(f"Connecting to {settings.DATABASE_URL}...")

    if settings.DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_engine(
            settings.DATABASE_URL,
            echo=True,
            pool_pre_ping=True,
        )

    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    # Check if tables exist
    print("\nExisting tables:")
    print(inspect(engine).get_table_names())


if __name__ == "__main__":
    init_db()
