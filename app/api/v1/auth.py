from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.core.security import verify_google_token, create_access_token

router = APIRouter()


class Token(BaseModel):
    access_token: str
    token_type: str


class GoogleLogin(BaseModel):
    id_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


@router.post("/google", response_model=LoginResponse)
async def google_login(payload: GoogleLogin, db: Session = Depends(get_db)):
    """
    Exchanges a Google ID Token for a backend JWT access token.
    If the user does not exist, they will be registered automatically.
    """
    # 1. Verify token with Google
    try:
        idinfo = await verify_google_token(payload.id_token)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )

    google_id = idinfo.get("sub")
    email = idinfo.get("email")
    name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account must have an email address"
        )

    # 2. Find or create user
    user = db.query(User).filter(User.google_id == google_id).first()
    
    # Alternatively, check by email if the user registered with another provider,
    # but since Google is the only provider for now, we look up by google_id or email
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # User exists but google_id is not set (e.g. pre-existing email placeholder)
            user.google_id = google_id
            user.full_name = name
            user.avatar_url = picture
            db.commit()
            db.refresh(user)
        else:
            # Create a completely new user
            user = User(
                google_id=google_id,
                email=email,
                full_name=name,
                avatar_url=picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        # Update user profile details from Google if they have changed
        updated = False
        if user.full_name != name:
            user.full_name = name
            updated = True
        if user.avatar_url != picture:
            user.avatar_url = picture
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    # 3. Create access token
    access_token = create_access_token(subject=user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns the profile of the currently logged-in user.
    """
    return current_user
