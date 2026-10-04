"""
Database initialization routines.
Creates data directories and runs idempotent table creation without inserting fake data.
"""

from pathlib import Path
from typing import Optional
from sqlalchemy import Engine

from app.core.config import DEFAULT_DATA_DIR, settings
from app.db.session import engine as default_engine
from app.models.base import Base
# Import models to ensure they are registered with Base.metadata before create_all
import app.models  # noqa: F401


def init_db(target_engine: Optional[Engine] = None) -> None:
    """
    Initializes database schema idempotently.

    1. Creates target directory (e.g. data/) if writing to a file-based SQLite database.
    2. Invokes Base.metadata.create_all to instantiate tables if absent.
    3. Guarantees no mock/demo records are inserted.
    4. Safe to execute multiple times across restarts.
    """
    eng = target_engine or default_engine

    # Ensure local directory exists for file-based SQLite databases
    db_url = str(eng.url)
    if db_url.startswith("sqlite:///") and ":memory:" not in db_url:
        db_path_str = db_url.replace("sqlite:///", "")
        db_path = Path(db_path_str).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    elif DEFAULT_DATA_DIR:
        DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Idempotently create tables from registered metadata
    Base.metadata.create_all(bind=eng)


if __name__ == "__main__":
    init_db()
    print("Database tables initialized successfully.")
