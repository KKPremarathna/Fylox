# Fylox: Next-Gen Agentic Ticket Management

Fylox is a comprehensive customer support platform built for the Advanced Agentic Coding capstone. It fuses isolated microservice execution paths with deterministic hybrid AI routing boundaries to securely triage customer issues without exposing irreversible financial side-effects (e.g. refunds).

## 🪐 Architecture Overview
The application uses a 3-tier production alignment spanning **React (Vite/TypeScript)** on the frontend, **FastAPI (Python)** on the backend, and **PostgreSQL** for strict relational data modeling. It integrates deterministic AI routing directly into standard REST controllers.

See `docs/architecture.mermaid` for the full deployment topology mapping.

## ✨ Key Features
- **AI Triage Router:** Dynamically routes natural language requests to internal agent domains (e.g., Shipping vs Billing). 
- **BOLA Protection:** Strict separation of resources preventing Customer A from interacting with Customer B's financial logic.
- **RAG Knowledge Base:** Deterministic chunked Markdown RAG returning highly contextual internal policy references securely.
- **Human-in-the-Loop Handoffs:** Safely intercepts and pauses sensitive AI deductions representing monetary values (Approval workflows).

## 🚀 Quick Start (Production Demo)

Deploy the full stack rapidly utilizing Docker Compose:

```bash
# 1. Boot up the network
docker compose up --build -d

# 2. Seed the development environment
docker compose exec backend python /app/scripts/seed_demo_data.py
```

Open a browser to `http://localhost`.

### Demo Accounts
- **Admin**: `admin@fylox.com` / `password123`
- **Customer 1**: `customer1@demo.com` / `password123`
- **Customer 2**: `customer2@demo.com` / `password123`

Check out `docs/demo-guide.md` for a complete 3-minute walkthrough script testing the exact security layers.

## 🛠 Local Development Options

If evaluating logic independently from Docker:

**Backend:**
```bash
python -m venv myenv
source myenv/Scripts/activate # Windows
pip install -r apps/requirements.txt
# Copy .env.example to .env
# Run SQLite in-memory:
PYTHONPATH=apps pytest -v apps/tests
```

**Frontend:**
```bash
cd apps/frontend
npm ci
npm run build
```