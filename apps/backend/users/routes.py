from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.backend.database import get_db
from apps.backend.users.models import User
from apps.backend.users.schemas import userCreate, userResponse
from apps.backend.security import hash_password,verify_password

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# Add user
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

# Get all users
@router.get("", response_model=list[userResponse])
def list_users(db: Session = Depends(get_db)):
    statement = select(User).order_by(User.created_at.desc())
    users = db.scalars(statement).all()

    return users

# Get user by userId
@router.get("/{user_id}", response_model=userResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user

