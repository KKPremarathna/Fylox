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
from backend.activity.models import TicketActivity
from backend.approvals.models import ApprovalRequest
from backend.messages.models import TicketMessage
from backend.orders.models import Order
from backend.payments.models import Payment
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
    # app.dependency_overrides is cleared by the base client fixture.

@pytest.fixture(scope="function")
def customer_client(client, customer_user):
    app.dependency_overrides[get_current_user] = lambda: customer_user
    yield client
    # app.dependency_overrides is cleared by the base client fixture.


@pytest.fixture(scope="function")
def second_customer_user(db_session):
    """A second distinct customer who does not own customer_ticket."""
    user = User(
        username="other_customer",
        email="other@example.com",
        password_hash="fakehash",
        role="CUSTOMER",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def second_customer_client(client, second_customer_user):
    """TestClient authenticated as the second (non-owning) customer."""
    app.dependency_overrides[get_current_user] = lambda: second_customer_user
    yield client
    # app.dependency_overrides is cleared by the base client fixture.


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


@pytest.fixture(scope="function")
def customer_order(db_session, customer_user):
    from decimal import Decimal
    from backend.orders.models import Order
    order = Order(
        order_number="ORD-1001",
        customer_id=customer_user.user_id,
        status="PENDING",
        total_amount=Decimal("149.99"),
        currency="USD",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture(scope="function")
def second_customer_order(db_session, second_customer_user):
    from decimal import Decimal
    from backend.orders.models import Order
    order = Order(
        order_number="ORD-1002",
        customer_id=second_customer_user.user_id,
        status="SHIPPED",
        total_amount=Decimal("250.00"),
        currency="USD",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.fixture(scope="function")
def customer_payment(db_session, customer_order):
    from decimal import Decimal
    from backend.payments.models import Payment
    payment = Payment(
        order_id=customer_order.id,
        provider_reference="ch_cust_123",
        amount=Decimal("149.99"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    return payment


@pytest.fixture(scope="function")
def second_customer_payment(db_session, second_customer_order):
    from decimal import Decimal
    from backend.payments.models import Payment
    payment = Payment(
        order_id=second_customer_order.id,
        provider_reference="ch_second_456",
        amount=Decimal("250.00"),
        currency="USD",
        status="SUCCEEDED",
        payment_method="CARD",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)
    return payment