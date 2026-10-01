import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone

# Add 'apps' to sys.path so we can import backend reliably
sys.path.append(str(Path(__file__).parent.parent / "apps"))

from backend.database import SessionLocal, engine, Base
from backend.security import get_password_hash
from backend.users.models import User
from backend.tickets.models import Ticket
from backend.messages.models import TicketMessage
from backend.orders.models import Order
from backend.payments.models import Payment
from backend.shipments.models import Shipment
from backend.policies.models import PolicyDocument, PolicyChunk
from backend.approvals.models import ApprovalRequest


def seed_data():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(User).count() > 0:
            print("Database already seeded. Skipping...")
            return

        print("Seeding Users...")
        admin = User(username="admin", email="admin@fylox.com", hashed_password=get_password_hash("password123"), role="ADMIN")
        cust1 = User(username="customer1", email="customer1@demo.com", hashed_password=get_password_hash("password123"), role="CUSTOMER")
        cust2 = User(username="customer2", email="customer2@demo.com", hashed_password=get_password_hash("password123"), role="CUSTOMER")
        
        db.add_all([admin, cust1, cust2])
        db.commit()
        db.refresh(admin)
        db.refresh(cust1)
        db.refresh(cust2)

        print("Seeding Policies...")
        policy = PolicyDocument(
            title="Refund Policy",
            version="v1.0",
            status="APPROVED",
            content="# Refunds\n\nRefunds are allowed within 14 days of purchase for unused items.\n\n# Duplicate Charges\n\nIf you were billed twice, our system will flag it and a human agent will quickly issue a refund review."
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        
        chunk1 = PolicyChunk(document_id=policy.id, section_heading="Refunds", content_snippet="Refunds are allowed within 14 days of purchase for unused items.", chunk_index=0)
        chunk2 = PolicyChunk(document_id=policy.id, section_heading="Duplicate Charges", content_snippet="If you were billed twice, our system will flag it and a human agent will quickly issue a refund review.", chunk_index=1)
        db.add_all([chunk1, chunk2])

        print("Seeding Orders, Payments, & Shipments...")
        # Cust1 - Has a clean order
        order1 = Order(customer_id=cust1.user_id, order_number="ORD-1001", total_amount="125.00", currency="USD", status="SHIPPED")
        db.add(order1)
        db.commit()
        db.refresh(order1)
        pay1 = Payment(order_id=order1.id, amount=125.0, currency="USD", status="SUCCEEDED", provider_reference="str-1001")
        ship1 = Shipment(order_id=order1.id, carrier="DHL", tracking_number="DHL12345678", status="IN_TRANSIT")
        db.add_all([pay1, ship1])

        # Cust2 - Has a duplicate charge issue
        order2 = Order(customer_id=cust2.user_id, order_number="ORD-2002", total_amount="75.00", currency="USD", status="PROCESSING")
        db.add(order2)
        db.commit()
        db.refresh(order2)
        pay2a = Payment(order_id=order2.id, amount=75.0, currency="USD", status="SUCCEEDED", provider_reference="str-2002a")
        pay2b = Payment(order_id=order2.id, amount=75.0, currency="USD", status="SUCCEEDED", provider_reference="str-2002b") # The duplicate!
        db.add_all([pay2a, pay2b])

        print("Seeding Tickets & Approvals...")
        ticket1 = Ticket(customer_id=cust1.user_id, subject="Where is my shipment?", description="It has been a few days.", status="OPEN", final_category="ORDER_SUPPORT")
        ticket2 = Ticket(customer_id=cust2.user_id, subject="I was charged twice", description="Can someone refund the duplicate charge?", status="IN_PROGRESS", final_category="BILLING_PAYMENT")
        db.add_all([ticket1, ticket2])
        db.commit()
        db.refresh(ticket1)
        db.refresh(ticket2)

        msg1 = TicketMessage(ticket_id=ticket1.id, sender_id=cust1.user_id, sender_type="CUSTOMER", content="I would like an update on ORD-1001.")
        msg2 = TicketMessage(ticket_id=ticket2.id, sender_id=cust2.user_id, sender_type="CUSTOMER", content="I noticed on my card two $75 charges.")
        db.add_all([msg1, msg2])
        
        # Pending refund logic
        evidence = json.dumps({"duplicate_groups": [{"amount": "75.0", "currency": "USD", "payment_count": 2}], "successful_payment_count": 2})
        approval = ApprovalRequest(ticket_id=ticket2.id, order_id=order2.id, request_type="REFUND_REVIEW", status="PENDING", reason="Customer spotted a duplicate 75.00 USD charge", evidence_json=evidence)
        db.add(approval)
        db.commit()

        print("Demo Database Seeded Successfully!")
        print("Test Credentials:")
        print("  Admin: admin@fylox.com / password123")
        print("  Cust1: customer1@demo.com / password123")
        print("  Cust2: customer2@demo.com / password123")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
