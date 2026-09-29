from fastapi import FastAPI

from backend.auth.routes import router as auth_router
from backend.tickets.routes import router as tickets_router
from backend.users.routes import router as users_router
from backend.messages.routes import router as messages_router
from backend.admin.routes import router as admin_router

app = FastAPI(
    title="Fylox API",
    description="Backend API for an AI-assisted customer-support platform.",
    version="0.4.0",
)

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(messages_router)
app.include_router(admin_router)


@app.get("/")
def read_root():
    return {
        "message": "Fylox API is running",
        "stage": "ticket ownership and admin workflow",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }