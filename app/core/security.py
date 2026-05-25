import httpx
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from fastapi import HTTPException, status
from jose import jwt

from app.core.config import settings

ALGORITHM = "HS256"


async def verify_google_token(token: str) -> dict:
    """
    Verifies a Google ID token by calling the Google tokeninfo API.
    Returns the parsed token claims if valid.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Client ID is not configured on the server."
        )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={token}",
                timeout=5.0
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to Google verification server: {exc}"
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )

        idinfo = response.json()

        # Verify audience (aud claim)
        # Note: In some scenarios where multiple client IDs are used (e.g., iOS and Web),
        # this might need to support a list, but for now we match GOOGLE_CLIENT_ID.
        if idinfo.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token audience mismatch"
            )

        # Verify issuer (iss claim)
        if idinfo.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer invalid"
            )

        return idinfo


def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """
    Creates a signed JWT access token for a user.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode = {
        "exp": expire,
        "sub": str(subject)
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
