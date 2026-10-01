from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.security import hash_password, verify_password
from backend.users.models import User
from backend.users.schemas import userCreate, userResponse

router = APIRouter(
    prefix="/users",
    tags=["Users"],
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
    clean_email = user.email.strip().lower()
    clean_username = user.username.strip()

    # Pre-check for duplicate email or username
    existing_user = db.scalar(
        select(User).where(
            (func.lower(User.email) == clean_email)
            | (func.lower(User.username) == clean_username.lower())
        )
    )
    if existing_user:
        if existing_user.email.lower() == clean_email:
            detail = "An account with this email address already exists"
        else:
            detail = "An account with this username already exists"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    new_user = User(
        username=clean_username,
        email=clean_email,
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
            detail="An account with this email or username already exists",
        )

    return new_user
