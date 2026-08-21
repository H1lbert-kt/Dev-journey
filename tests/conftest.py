import pytest
from fastapi.testclient import TestClient
from app.database.connection import init_database, SessionLocal, engine, Base
from app.models.user import User
from app.utils.auth import hash_password, create_session


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_rate_limits():
    """Reset rate limit state before each test to prevent bleed."""
    from main import _rate_limit_instances
    for inst in _rate_limit_instances:
        inst._requests.clear()
        inst._login_attempts.clear()
        inst._register_attempts.clear()
    yield
    for inst in _rate_limit_instances:
        inst._requests.clear()
        inst._login_attempts.clear()
        inst._register_attempts.clear()


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client():
    from main import app
    c = TestClient(app, raise_server_exceptions=False)
    return c


@pytest.fixture
def rate_limit_client():
    """Client for testing rate limiting - uses fresh app to get clean state."""
    from main import app
    c = TestClient(app, raise_server_exceptions=False)
    return c


@pytest.fixture
def user_a(db):
    user = User(
        username="user_a",
        email="a@test.com",
        password_hash=hash_password("pass_a123"),
        study_mode="programacao",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_b(db):
    user = User(
        username="user_b",
        email="b@test.com",
        password_hash=hash_password("pass_b123"),
        study_mode="concursos",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def token_a(db, user_a):
    return create_session(user_a.id, db)


@pytest.fixture
def token_b(db, user_b):
    return create_session(user_b.id, db)


@pytest.fixture
def auth_client_a(client, token_a):
    c = TestClient(client.app, raise_server_exceptions=False)
    c.cookies.set("session_token", token_a)
    c.cookies.set("study_mode", "programacao")
    return c


@pytest.fixture
def auth_client_b(client, token_b):
    c = TestClient(client.app, raise_server_exceptions=False)
    c.cookies.set("session_token", token_b)
    c.cookies.set("study_mode", "concursos")
    return c
