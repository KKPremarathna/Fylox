from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth.schemas import TokenResponse
from backend.database import get_db
from backend.security import (
    create_access_token,
    get_current_user,
    verify_password,
)
from backend.users.models import User
from backend.users.schemas import userResponse

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    identifier = form_data.username.strip().lower()

    statement = select(User).where(
        (func.lower(User.email) == identifier) | (func.lower(User.username) == identifier)
    )
    user = db.scalar(statement)

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email, username, or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        raise invalid_credentials

    if not verify_password(form_data.password, user.password_hash):
        raise invalid_credentials

    access_token = create_access_token(
        subject=str(user.user_id),
        role=user.role,
    )

    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=userResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return current_user