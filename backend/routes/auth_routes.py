"""Authentication routes"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy import select, insert

from models import UserCreate, UserResponse, Token, LoginRequest
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from database import async_session, users

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Register a new user"""
    async with async_session() as session:
        # Check if email exists
        result = await session.execute(select(users).where(users.c.email == user.email))
        if result.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Check if username exists
        result = await session.execute(select(users).where(users.c.username == user.username))
        if result.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

        # Create user
        hashed_password = get_password_hash(user.password)
        result = await session.execute(
            insert(users).values(
                email=user.email,
                username=user.username,
                hashed_password=hashed_password,
                is_active=True
            )
        )
        await session.commit()
        user_id = result.inserted_primary_key[0]

        # Fetch created user
        result = await session.execute(select(users).where(users.c.id == user_id))
        new_user = result.first()

        return UserResponse(**dict(new_user._mapping))


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Login and get access token"""
    async with async_session() as session:
        # Find user
        result = await session.execute(select(users).where(users.c.email == login_data.email))
        user_row = result.first()

        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = dict(user_row._mapping)

        if not verify_password(login_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"]}, expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer")


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible login endpoint"""
    async with async_session() as session:
        # Find user (OAuth2 uses username field, but we use email)
        result = await session.execute(select(users).where(users.c.email == form_data.username))
        user_row = result.first()

        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = dict(user_row._mapping)

        if not verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"]}, expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """Get current user info"""
    return UserResponse(**current_user)
