"""Run the real Alembic migrations on an empty schema, the way a brand-new production database sees them."""
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.models import Base

BACKEND = Path(__file__).resolve().parents[1]
BASE_URL = os.environ["DATABASE_URL"].split("?")[0]
SCHEMA = "migtest"


def alembic(*args):
    env = {**os.environ, "DATABASE_URL": f"{BASE_URL}?options=-csearch_path%3D{SCHEMA}"}
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env,
                          capture_output=True, text=True)


def test_migrations_build_the_full_schema_from_scratch():
    engine = create_engine(BASE_URL)
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA {SCHEMA}"))
    try:
        up = alembic("upgrade", "head")
        assert up.returncode == 0, up.stderr
        tables = set(inspect(engine).get_table_names(schema=SCHEMA)) - {"alembic_version"}
        assert tables == set(Base.metadata.tables)

        drift = alembic("check")  # models and migrations must agree
        assert drift.returncode == 0, drift.stdout + drift.stderr

        assert alembic("downgrade", "base").returncode == 0
        assert alembic("upgrade", "head").returncode == 0
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        engine.dispose()
