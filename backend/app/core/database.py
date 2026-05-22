import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./Project.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    logger.info("Database backend: SQLite (%s)", DATABASE_URL)
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,   # recycle connections before cloud DBs drop idle ones (~30 min)
        pool_pre_ping=True,  # verify connection is alive before handing it out
    )
    # Log the host only (strip credentials from the URL for safe logging)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        logger.info("Database backend: PostgreSQL (%s/%s)", parsed.hostname, (parsed.path or "").lstrip("/"))
    except Exception:
        logger.info("Database backend: PostgreSQL")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
