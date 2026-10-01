# Fylox Demo Guide

This guide provides a rapid 3-to-5-minute walkthrough of the core features in the Fylox capstone project to demonstrate the secure AI routing, payment abstractions, and admin access controls.

## Prerequisites
Ensure the application is running via Docker Compose and the database is seeded.
```bash
docker compose up --build -d
docker compose exec backend python /app/scripts/seed_demo_data.py
```
Open `http://localhost` in your local browser.

## Step 1: Customer Observation
**Login as Customer 1:**
- Email: `customer1@demo.com`
- Password: `password123`

**Action:**
1. Navigate to **My Orders**. Observe `ORD-1001` and its clean `SHIPPED` status.
2. Navigate to **Support Tickets**. Click on the ticket "Where is my shipment?".
3. Attempt to interact with the AI assistant. Ensure the fast-path safely guides the customer based on `ORDER_SUPPORT`.

## Step 2: The Billing Edge Case
**Login as Customer 2:**
- Email: `customer2@demo.com`
- Password: `password123`

**Action:**
1. Navigate to **My Orders**. Observe `ORD-2002` safely bound to this user (Customer 1's orders are hidden).
2. Click on the order to securely execute the "Check Charges" pipeline on the backend.
3. In the ticket details view for "I was charged twice", use the **Ask AI** feature.
4. Type: *"Refund my duplicate charge now!"*
5. Assure the AI responds with an explicit Human-Escalation blocker (action taken: `ROUTED_WITHOUT_REPLY` / AI generated placeholder). It should not promise a refund directly.

## Step 3: Admin Triage & Resolution
**Login as Admin:**
- Email: `admin@fylox.com`
- Password: `password123`

**Action:**
1. Navigate to **Tickets** and open Customer 2's ticket.
2. Notice the `Category Review` panel accurately surfaces the AI confident assessment (`BILLING_SUPPORT` / `HUMAN_ESCALATION`).
3. Accept the AI suggestion manually to override the final category.
4. Check the **Activity Timeline** inside the ticket to review the forensics JSON logging of the AI router securely logging the payload metadata.
5. Navigate to **Refund Queue** and mark Customer 2's `PENDING` request as `APPROVED`.

## Conclusion 
The UI natively combines React SPA routing with Python event loops driven by Docker networks without CORS complications. Highly restricted agent behaviors enforce revenue security perfectly!
