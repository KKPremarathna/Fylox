# Fylox

**Fylox** is a modern, full-stack customer support ticketing and approval management platform featuring AI-assisted ticket category suggestions, automated duplicate payment evidence auditing, and real-time activity history logs.

---

## Key Features

- **Support Ticketing & Management**: Customers create tickets; support agents and admins review, assign, and update ticket statuses.
- **AI Category Suggestions**: Smart automated category classification with fallback heuristics for offline/demo reliability (`BILLING_PAYMENT`, `ORDER_SUPPORT`, `ACCOUNT_SUPPORT`, `GENERAL_SUPPORT`).
- **Refund Review & Approvals**: Admin approval workflow for customer refund requests, complete with duplicate charge evidence summaries.
- **System Activity Audit**: Real-time activity timeline tracking system events, actor actions, AI suggestions, and decision logs.
- **Flexible Auth**: Support for authentication using either **Email Address** or **Username** with JWT token validation.

---

## Tech Stack

- **Frontend**: React (Vite, TypeScript), served via Nginx reverse proxy
- **Backend**: FastAPI (Python 3.11), SQLAlchemy ORM, Pydantic v2
- **Database**: PostgreSQL 15
- **Orchestration**: Docker & Docker Compose

---

## Repository Layout

```text
apps/
  backend/           # FastAPI application, database models, ML service, and routes
    activity/        # System event logging & audit history
    approvals/       # Refund review & approval requests
    auth/            # User authentication & JWT management
    ml/              # AI category suggestion classifier
    tickets/         # Support ticket creation & management
    users/           # User accounts & roles
  frontend/          # React + Vite TypeScript single-page application
scripts/
  seed_demo_data.py  # Reset & seed demo database script
docker-compose.yml   # Multi-container local stack definition
Dockerfile.backend  # Backend container definition
Dockerfile.frontend # Frontend + Nginx container definition
```

---

## Environment Configuration

Copy or create a `.env` file in the root directory for optional key overrides:

```env
DATABASE_URL=postgresql+psycopg2://admin:password@db:5432/fylox
JWT_SECRET_KEY=super_secret_demo_key
OPENAI_API_KEY=
```

---

## Quick Start (Docker Compose)

### 1. Start Containers
Launch PostgreSQL, the FastAPI backend, and the React Nginx frontend:

```bash
docker compose up --build -d
```

### 2. Seed Demo Data
Reset and populate the database with demo users, orders, payments, shipments, and tickets:

```bash
docker compose exec backend python -u /app/scripts/seed_demo_data.py
```

### 3. Open in Browser
Access the web application at **[http://localhost](http://localhost)**.

---

## Demo Credentials

You can log in using either **Email** or **Username**:

| Role | Username | Email | Password |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin@fylox.com` | `password123` |
| **Customer 1** | `customer1` | `customer1@demo.com` | `password123` |
| **Customer 2** | `customer2` | `customer2@demo.com` | `password123` |

---

## Local Development (Outside Docker)

### Backend Development

```bash
cd apps/backend
pip install -r requirements.txt
uvicorn apps.backend.main:app --reload --port 8000
```

### Frontend Development

```bash
cd apps/frontend
npm install
npm run dev
```

---

## Troubleshooting & Tips

- **Container Code Syncing**: The `scripts/` and `apps/` directories are volume-mounted into the backend container for live code updating.
- **Rebuilding Containers**: If dependencies or Dockerfiles change, run `docker compose build --no-cache`.
- **Database Reset**: To start completely fresh, run `docker compose down -v` followed by `docker compose up -d` and the seed command.
