import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.security import get_current_user
from backend.tickets.rate_limit import reset_rate_limiter

# Import every model so all table definitions are registered in Base.metadata.
from backend.activity.models import TicketActivity
from backend.messages.models import TicketMessage
from backend.tickets.models import Ticket
from backend.users.models import User

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def client(db_session):
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def admin_user(db_session):
    user = User(
        username="admin_user",
        email="admin@example.com",
        password_hash="fakehash",
        role="ADMIN"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def customer_user(db_session):
    user = User(
        username="customer_user",
        email="customer@example.com",
        password_hash="fakehash",
        role="CUSTOMER"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def customer_ticket(db_session, customer_user):
    ticket = Ticket(
        customer_id=customer_user.user_id,
        subject="Sample ticket for AI",
        description="This is a test description",
        status="OPEN"
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket

@pytest.fixture(scope="function")
def admin_client(client, admin_user):
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def customer_client(client, customer_user):
    app.dependency_overrides[get_current_user] = lambda: customer_user
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """
    Runs automatically around every test function.
    Clears the in-memory sliding-window log before the test starts and again
    after it finishes, so no quota state leaks between test functions.
    """
    reset_rate_limiter()
    yield
    reset_rate_limiter()