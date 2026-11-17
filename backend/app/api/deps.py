"""
FastAPI Dependencies: Authentication & Security Injection
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.schemas.user import UserResponse

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)

# In-memory user registry for Phase 6 authentication verification
USER_ACCOUNTS = {
    "mentor@cinematch.com": {
        "id": "usr_mentor_01",
        "email": "mentor@cinematch.com",
        "username": "mentor",
        "preferred_genres": ["Action", "Adventure", "Sci-Fi"],
        "is_active": True
    }
}


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserResponse:
    """
    Validates JWT Bearer token and returns authenticated User profile.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except (JWTError, ValidationError):
        raise credentials_exception

    user_data = USER_ACCOUNTS.get(email)
    if user_data:
        return UserResponse(**user_data)

    # Allow valid issued tokens to authenticate dynamically
    return UserResponse(
        id=f"usr_{abs(hash(email)) % 10000}",
        email=email,
        username=email.split("@")[0],
        preferred_genres=["Action", "Sci-Fi"],
        is_active=True
    )
