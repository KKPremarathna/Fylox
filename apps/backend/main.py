from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.routes import router as auth_router
from backend.tickets.routes import router as tickets_router
from backend.orders.routes import router as orders_router
from backend.payments.routes import router as payments_router
from backend.users.routes import router as users_router
from backend.messages.routes import router as messages_router
from backend.approvals.routes import customer_router as approvals_customer_router
from backend.approvals.routes import admin_router as approvals_admin_router
from backend.admin.routes import router as admin_router
from backend.activity.routes import admin_router as activity_admin_router
from backend.activity.routes import router as activity_router
from backend.shipments.routes import router as shipments_router
from backend.policies.routes import router as policies_router
from backend.policies.routes import admin_router as policies_admin_router
from backend.policies.routes import search_router as policy_search_router
from backend.ai.routes import router as ai_router
from backend.policies.routes import admin_router as policies_admin_router
from backend.policies.routes import search_router as policy_search_router

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
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(approvals_customer_router)
app.include_router(approvals_admin_router)
app.include_router(tickets_router)
app.include_router(messages_router)
app.include_router(admin_router)
app.include_router(activity_router)
app.include_router(activity_router)
app.include_router(activity_admin_router)
app.include_router(shipments_router)
app.include_router(policies_router)
app.include_router(policies_admin_router)
app.include_router(policy_search_router)
app.include_router(ai_router)

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