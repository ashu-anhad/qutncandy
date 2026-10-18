import os
import shutil
import tempfile

# Run tests in an isolated "test" schema inside the dev database (set before the app is imported).
_base_url = os.environ.get("DATABASE_URL", "postgresql+psycopg://candy:candy@localhost:5432/cutencandy")
os.environ["DATABASE_URL"] = f"{_base_url}?options=-csearch_path%3Dtest"
_media_dir = tempfile.mkdtemp(prefix="qc-media-")
os.environ["MEDIA_DIR"] = _media_dir

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def schema():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS test CASCADE"))
        conn.execute(text("CREATE SCHEMA test"))
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA test CASCADE"))
    shutil.rmtree(_media_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def signup(client, email="asha@example.com", password="secret123", name="Asha"):
    res = client.post("/api/auth/signup", json={"name": name, "email": email, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def make_admin(client, email="admin@example.com"):
    from sqlalchemy import update

    from app.auth.models import User
    from app.core.db import SessionLocal

    token = signup(client, email=email, name="Admin")["access_token"]
    with SessionLocal() as db:
        db.execute(update(User).where(User.email == email).values(role="admin"))
        db.commit()
    return auth_header(token)
