"""Suite-wide test isolation: every test gets its own empty in-memory database, seeded like a fresh install.

Why: the application database (data/envirochem.sqlite) is persistent and shared. Tests that write to it leave rows
behind on every run, and tests that need unique values (CAS numbers, file hashes) collide with those leftovers
with growing probability, which showed up as intermittent 409 failures. It also polluted real project data with
tens of test projects per run.

How: the `get_db` dependency and every `SessionLocal` reference (the app's startup seeding and tests that open
sessions directly) are pointed at a private in-memory SQLite database that has been seeded with the same seed the
app runs on startup. Nothing a test does touches data/envirochem.sqlite. Tests that need a different setup can
still install their own override; it replaces this one for the duration of the test.
"""

from __future__ import annotations

import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.database import Base, get_db
from app.main import app
from app.seed import seed

_ORIGINAL_SESSION_LOCAL = database.SessionLocal


@pytest.fixture(autouse=True)
def isolated_app_database(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        seed(db)
        db.commit()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    # Code that imported SessionLocal by name (the app's lifespan seeding, some tests) keeps its own reference.
    for module in list(sys.modules.values()):
        if getattr(module, "SessionLocal", None) is _ORIGINAL_SESSION_LOCAL:
            monkeypatch.setattr(module, "SessionLocal", Session)
    try:
        yield Session
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
