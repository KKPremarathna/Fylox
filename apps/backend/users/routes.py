from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.users.models import User
from backend.users.schemas import userCreate, userResponse
from backend.security import hash_password,verify_password

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# Add user / Register
@router.post(
    "",
    response_model=userResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user: userCreate,
    db: Session = Depends(get_db),
):
    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    return new_user
