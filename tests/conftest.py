"""Test setup: point the app at a throwaway database and rebuild it before each test.

Create the database once with `createdb pike_alumni_test`, then run `pytest`.
Override with TEST_DATABASE_URL if yours lives elsewhere.
"""

import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# These must be set before app/db import, because load_dotenv() never
# overrides variables that already exist.
TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql://localhost/pike_alumni_test")
if not TEST_DB.rstrip("/").endswith("_test"):
    raise RuntimeError("Refusing to run tests: the test database name must end in _test")
os.environ["DATABASE_URL"] = TEST_DB
os.environ["SECRET_KEY"] = "test-secret-key"

from werkzeug.security import generate_password_hash  # noqa: E402

from app import app as flask_app  # noqa: E402
from db import connect  # noqa: E402

SQL_FILES = ["schema.sql", "members.sql", "tracking.sql"]
PASSWORD = "correct-horse"
CSRF = "test-csrf-token"


@pytest.fixture(autouse=True)
def fresh_db():
    with connect() as conn:
        conn.execute(
            "DROP TABLE IF EXISTS contact_events, search_events, settings, members CASCADE"
        )
        for name in SQL_FILES:
            conn.execute((ROOT / "sql" / name).read_text())
    yield


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        with client.session_transaction() as sess:
            sess["csrf"] = CSRF
        yield client


def make_member(email, password=PASSWORD, is_admin=False):
    """Insert a member (password=None means invited but not signed up). Returns id."""
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO members (email, password_hash, is_admin, activated_at)
            VALUES (%s, %s, %s, CASE WHEN %s THEN now() END)
            RETURNING id
            """,
            (
                email,
                generate_password_hash(password) if password else None,
                is_admin,
                password is not None,
            ),
        ).fetchone()
        return row["id"]


def post(client, url, data=None, **kwargs):
    """POST a form with a valid CSRF token (re-seeded, since logout clears the session)."""
    with client.session_transaction() as sess:
        sess["csrf"] = CSRF
    data = dict(data or {})
    data.setdefault("csrf", CSRF)
    return client.post(url, data=data, **kwargs)


def login(client, email, password=PASSWORD):
    return post(client, "/login", {"email": email, "password": password})


def query(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchall()
