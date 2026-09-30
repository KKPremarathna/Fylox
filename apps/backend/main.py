from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.routes import router as auth_router
from backend.tickets.routes import router as tickets_router
from backend.users.routes import router as users_router
from backend.messages.routes import router as messages_router
from backend.admin.routes import router as admin_router
from backend.activity.routes import router as activity_router

app = FastAPI(
    title="Fylox API",
    description="Backend API for an AI-assisted customer-support platform.",
    version="0.4.0",
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(messages_router)
app.include_router(admin_router)
app.include_router(activity_router)

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