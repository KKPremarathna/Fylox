# Fylox

Fylox is an AI-assisted customer-support platform being built as a full-stack learning project.

## Current Progress

### Stage 1C — FastAPI and PostgreSQL Foundation

- FastAPI backend initialized
- PostgreSQL connected through SQLAlchemy
- Ticket database model created
- Ticket creation and retrieval endpoints implemented
- Pydantic request/response validation added
- Basic API tests created with pytest
- Interactive API documentation available through FastAPI Swagger UI

## Current API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API information |
| GET | `/health` | Health check |
| POST | `/tickets` | Create a support ticket |
| GET | `/tickets` | List support tickets |
| GET | `/tickets/{ticket_id}` | Get one support ticket |

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Psycopg
- Pytest

## Local Setup

### 1. Clone the repository

```bash
git clone [https://github.com/YOUR_GITHUB_USERNAME/fylox.git](https://github.com/YOUR_GITHUB_USERNAME/fylox.git)
cd fylox
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv myenv
.\myenv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r apps/backend/requirements.txt
```

### 4. Configure environment variables

Copy the template:

```powershell
Copy-Item .env.example .env
```

Update `DATABASE_URL` in `.env` with your PostgreSQL username, password, host, port, and database name.

### 5. Run the API

```powershell
cd apps
uvicorn backend.main:app --reload
```

Open API documentation:

```text
http://127.0.0.1:8000/docs
```

### 6. Run tests

From the `apps` directory:

```powershell
pytest -v
```

## Project Structure

```text
fylox/
├── apps/
│   ├── backend/
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   └── tests/
│       └── test_main.py
├── .env.example
├── .gitignore
└── README.md
```

## Roadmap

- [x] Set up FastAPI project
- [x] Connect PostgreSQL database
- [x] Build basic ticket CRUD foundation
- [x] Add endpoint tests
- [ ] Add Alembic database migrations
- [ ] Add authentication and role-based access control
- [ ] Add customer/admin dashboards
- [ ] Add ticket messages and ticket-status updates
- [ ] Add order/payment mock data
- [ ] Add RAG-powered knowledge base
- [ ] Add AI ticket routing and specialist agents
- [ ] Add human approval workflows
- [ ] Deploy with Docker and CI/CD