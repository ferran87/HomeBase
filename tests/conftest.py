import uuid
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.models.base import Base
from app.models.user import User
from app.db.database import get_db

TEST_DATABASE_URL = "sqlite:///:memory:"

# StaticPool ensures all connections (including those made from TestClient's thread)
# share the same in-memory SQLite database, so tables created in the fixture are
# visible to the HTTP request handler.
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable FK support and relax type checking for SQLite test compat."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def db():
    """Create a fresh DB with tables for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client wired to the test DB session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def two_users(db):
    """Seed the two parent users used across tests."""
    parent1 = User(id=uuid.uuid4(), name="Ferran", email="ferran@example.com")
    parent2 = User(id=uuid.uuid4(), name="Marta", email="marta@example.com")
    db.add_all([parent1, parent2])
    db.commit()
    return parent1, parent2
