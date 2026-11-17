"""
Authentication & User Account Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from backend.app.schemas.user import UserCreate, UserLogin, TokenResponse, UserResponse
from backend.app.core.security import get_password_hash, verify_password, create_access_token
from backend.app.api.deps import get_current_user, USER_ACCOUNTS

router = APIRouter()

# Password database simulation
PASSWORD_HASH_STORE = {
    "mentor@cinematch.com": get_password_hash("Mentor123!"),
}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate):
    """Registers a new user account with hashed password credentials."""
    if user_in.email in USER_ACCOUNTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    hashed_pw = get_password_hash(user_in.password)
    new_user = {
        "id": f"usr_{abs(hash(user_in.email)) % 10000}",
        "email": user_in.email,
        "username": user_in.username,
        "preferred_genres": user_in.preferred_genres,
        "is_active": True
    }
    USER_ACCOUNTS[user_in.email] = new_user
    PASSWORD_HASH_STORE[user_in.email] = hashed_pw

    return UserResponse(**new_user)


@router.post("/login", response_model=TokenResponse)
async def login_user(credentials: UserLogin):
    """Authenticates credentials and issues a signed JWT access token."""
    stored_hash = PASSWORD_HASH_STORE.get(credentials.email)
    if not stored_hash or not verify_password(credentials.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = USER_ACCOUNTS.get(credentials.email)
    token = create_access_token(subject=credentials.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user["id"] if user else "usr_demo",
        username=user["username"] if user else credentials.email.split("@")[0]
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user from their JWT Bearer token."""
    return current_user
