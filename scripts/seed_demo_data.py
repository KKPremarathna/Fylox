import sys
from pathlib import Path

from sqlalchemy import inspect, select, text

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / "apps"),
)

from backend.database import Base, engine, SessionLocal
from backend.security import hash_password
from backend.users.models import User
from backend.tickets.models import Ticket
from backend.activity.models import TicketActivity
from backend.messages.models import TicketMessage
from backend.orders.models import Order
from backend.payments.models import Payment
from backend.shipments.models import Shipment
from backend.policies.models import PolicyDocument, PolicyChunk
from backend.approvals.models import ApprovalRequest
from backend.ai.models import BillingAnalysisRecord


def check_seed_database() -> None:
    with engine.connect() as conn:
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())
        required_tables = set(Base.metadata.tables)

        missing_tables = required_tables - existing_tables

        if missing_tables:
            raise RuntimeError(
                "Missing tables: "
                + ", ".join(sorted(missing_tables))
                + ". Apply Alembic migrations before seeding."
            )

        if "alembic_version" not in existing_tables:
            raise RuntimeError(
                "Alembic tracking is missing. Refusing to seed."
            )

        revisions = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()

        if not revisions:
            raise RuntimeError(
                "Alembic revision is empty. "
                "Apply migrations before seeding."
            )

        nonempty_tables = []

        for table in Base.metadata.sorted_tables:
            row = conn.execute(
                select(table).limit(1)
            ).first()

            if row is not None:
                nonempty_tables.append(table.name)

        if nonempty_tables:
            raise RuntimeError(
                "Refusing to seed a non-empty database. "
                "Tables containing data: "
                + ", ".join(sorted(nonempty_tables))
            )


def seed_data() -> None:
    print(
        "Checking migrated schema and empty demo database: "
        f"{engine.url.database}"
    )
    check_seed_database()

    with SessionLocal() as db:
        try:
            print("Seeding users...")

            admin = User(
                username="admin",
                email="admin@fylox.com",
                password_hash=hash_password("password123"),
                role="ADMIN",
            )
            cust1 = User(
                username="customer1",
                email="customer1@demo.com",
                password_hash=hash_password("password123"),
                role="CUSTOMER",
            )
            cust2 = User(
                username="customer2",
                email="customer2@demo.com",
                password_hash=hash_password("password123"),
                role="CUSTOMER",
            )

            db.add_all([admin, cust1, cust2])
            db.flush()

            print("Seeding policies...")

            policy = PolicyDocument(
                title="Refund Policy",
                version="v1.0",
                status="APPROVED",
                content=(
                    "# Refunds\n\n"
                    "Refunds are allowed within 14 days "
                    "of purchase for unused items.\n\n"
                    "# Duplicate Charges\n\n"
                    "If you were billed twice, our system "
                    "will flag it and a human agent will "
                    "quickly issue a refund review."
                ),
            )

            db.add(policy)
            db.flush()

            chunk1 = PolicyChunk(
                document_id=policy.id,
                section_heading="Refunds",
                content_snippet=(
                    "Refunds are allowed within 14 days "
                    "of purchase for unused items."
                ),
                chunk_index=0,
            )
            chunk2 = PolicyChunk(
                document_id=policy.id,
                section_heading="Duplicate Charges",
                content_snippet=(
                    "If you were billed twice, our system "
                    "will flag it and a human agent will "
                    "quickly issue a refund review."
                ),
                chunk_index=1,
            )

            db.add_all([chunk1, chunk2])

            print("Seeding orders, payments, and shipments...")

            order1 = Order(
                customer_id=cust1.user_id,
                order_number="ORD-1001",
                total_amount="125.00",
                currency="USD",
                status="SHIPPED",
            )
            order2 = Order(
                customer_id=cust2.user_id,
                order_number="ORD-2002",
                total_amount="75.00",
                currency="USD",
                status="PROCESSING",
            )

            db.add_all([order1, order2])
            db.flush()

            pay1 = Payment(
                order_id=order1.id,
                amount="125.00",
                currency="USD",
                status="SUCCEEDED",
                provider_reference="str-1001",
                payment_method="CARD",
            )
            ship1 = Shipment(
                order_id=order1.id,
                carrier="DHL",
                tracking_number="DHL12345678",
                status="IN_TRANSIT",
            )
            pay2a = Payment(
                order_id=order2.id,
                amount="75.00",
                currency="USD",
                status="SUCCEEDED",
                provider_reference="str-2002a",
                payment_method="CARD",
            )
            pay2b = Payment(
                order_id=order2.id,
                amount="75.00",
                currency="USD",
                status="SUCCEEDED",
                provider_reference="str-2002b",
                payment_method="CARD",
            )

            db.add_all([pay1, ship1, pay2a, pay2b])

            print("Seeding tickets and approvals...")

            ticket1 = Ticket(
                customer_id=cust1.user_id,
                subject="Where is my shipment?",
                description="It has been a few days.",
                status="OPEN",
                final_category="ORDER_SUPPORT",
            )
            ticket2 = Ticket(
                customer_id=cust2.user_id,
                subject="I was charged twice",
                description=(
                    "Can someone refund the duplicate charge?"
                ),
                status="IN_PROGRESS",
                final_category="BILLING_PAYMENT",
            )

            db.add_all([ticket1, ticket2])
            db.flush()

            msg1 = TicketMessage(
                ticket_id=ticket1.id,
                sender_id=cust1.user_id,
                sender_type="CUSTOMER",
                content="I would like an update on ORD-1001.",
            )
            msg2 = TicketMessage(
                ticket_id=ticket2.id,
                sender_id=cust2.user_id,
                sender_type="CUSTOMER",
                content="I noticed on my card two $75 charges.",
            )

            db.add_all([msg1, msg2])

            evidence = {
                "duplicate_groups": [
                    {
                        "amount": "75.0",
                        "currency": "USD",
                        "payment_count": 2,
                    }
                ],
                "successful_payment_count": 2,
            }

            approval = ApprovalRequest(
                ticket_id=ticket2.id,
                order_id=order2.id,
                request_type="REFUND_REVIEW",
                status="PENDING",
                requested_by_user_id=cust2.user_id,
                reason=(
                    "Customer spotted a duplicate "
                    "75.00 USD charge"
                ),
                evidence_json=evidence,
            )

            db.add(approval)
            db.commit()

        except Exception:
            db.rollback()
            raise

    print("Demo database seeded successfully!")
    print("----------------------------------")
    print("Demo-only credentials (login via username):")
    print("  Admin: admin / password123")
    print("  Customer 1: customer1 / password123")
    print("  Customer 2: customer2 / password123")


if __name__ == "__main__":
    seed_data()