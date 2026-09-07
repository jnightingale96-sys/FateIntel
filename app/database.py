from __future__ import annotations
from pathlib import Path
from time import perf_counter

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = settings.database_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def database_diagnostics() -> dict[str, object]:
    """Perform a real, credential-safe readiness query."""
    started = perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "backend": engine.url.get_backend_name(),
            "latency_ms": round((perf_counter() - started) * 1000, 3),
        }
    except Exception as exc:
        return {
            "status": "error",
            "backend": engine.url.get_backend_name(),
            "latency_ms": round((perf_counter() - started) * 1000, 3),
            "error_type": exc.__class__.__name__,
        }
