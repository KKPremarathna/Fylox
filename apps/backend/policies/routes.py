from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.admin.routes import require_admin
from backend.database import get_db
from backend.policies.models import PolicyDocument
from backend.policies.schemas import (
    PolicyDocumentCreate,
    PolicyDocumentPatch,
    PolicyDocumentSlimResponse,
    PolicyDocumentDetailResponse,
    PolicySearchResponse,
)
from backend.policies.service import ingest_markdown_policy, search_policies

router = APIRouter(
    prefix="/policies",
    tags=["Policies"]
)

admin_router = APIRouter(
    prefix="/admin/policies",
    tags=["Admin", "Policies"],
    dependencies=[Depends(require_admin)]
)


# --- Public / Customer-safe Routes ---

@router.get("", response_model=list[PolicyDocumentSlimResponse])
def list_policies(db: Session = Depends(get_db)):
    """Returns a list of all publicly APPROVED policies focusing purely on core metadata."""
    statement = (
        select(PolicyDocument)
        .where(PolicyDocument.status == "APPROVED")
        .order_by(PolicyDocument.title.asc())
    )
    return db.scalars(statement).all()


@router.get("/{policy_id}", response_model=PolicyDocumentDetailResponse)
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    """Returns a full document rendering if it is APPROVED."""
    doc = db.get(PolicyDocument, policy_id)
    if not doc or doc.status != "APPROVED":
        raise HTTPException(status_code=404, detail="Policy not found")
    return doc


# Note: Added directly to root-level for flexibility
search_router = APIRouter(tags=["Policies"])

@search_router.get("/policy-search", response_model=PolicySearchResponse)
def search_policy_knowledge(query: str = Query(...), db: Session = Depends(get_db)):
    """Performs retrieval over APPROVED policy chunks, filtering sensitive metadata."""
    results = search_policies(db=db, query=query)
    return {"query": query, "results": results}


# --- Admin Routes ---

@admin_router.post("", response_model=PolicyDocumentDetailResponse, status_code=201)
def create_policy(payload: PolicyDocumentCreate, db: Session = Depends(get_db)):
    """Ingests a markdown document, chunks it, and maps it strictly into DB."""
    return ingest_markdown_policy(db=db, payload=payload)


@admin_router.patch("/{policy_id}", response_model=PolicyDocumentDetailResponse)
def update_policy_status(
    policy_id: int, 
    payload: PolicyDocumentPatch, 
    db: Session = Depends(get_db)
):
    """Allows administrators to transition drafts, approve or archive legacy policies."""
    doc = db.get(PolicyDocument, policy_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    if payload.status:
        doc.status = payload.status
        db.commit()
        db.refresh(doc)
        
    return doc
