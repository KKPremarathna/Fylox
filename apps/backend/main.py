from fastapi import FastAPI

from backend.database import Base, engine
from backend.tickets.routes import router as ticket_router
from backend.users.routes import router as user_router
from backend.auth.routes import router as auth_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Fylox API",
    description="Backend API for an AI-assisted customer-support platform.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(ticket_router)


@app.get("/")
def read_root():
    return {
        "message": "Fylox API is running",
        "stage": "1C - PostgreSQL",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }