"""
Authentication API routes.

Provides endpoints for user registration, login, logout, and user information.
Handles JWT token creation and validation for secure API access.
"""
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger

from app.services.auth_service import auth_service, UserCreate, User
from app.database.connection import get_database, DatabaseManager
from config.settings import settings

router = APIRouter()


@router.post("/auth/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_create: UserCreate, db: DatabaseManager = Depends(get_database)
):
    """
    Register a new user
    """
    return await auth_service.create_user(user_create, db)


@router.post("/auth/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: DatabaseManager = Depends(get_database),
):
    """
    Login user and return access token
    """
    user = await auth_service.authenticate_user(
        form_data.username, form_data.password, db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )

    # Log login action
    await auth_service.log_user_action(user.id, "login", "auth", "", "", "", db=db)

    logger.info(f"User {user.username} logged in successfully")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": user,
    }


@router.get("/auth/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(auth_service.get_current_user),
):
    """
    Get current user information
    """
    return current_user


@router.post("/auth/logout")
async def logout_user(
    current_user: User = Depends(auth_service.get_current_user),
    db: DatabaseManager = Depends(get_database),
):
    """
    Logout user (for audit logging)
    """
    # Log logout action
    await auth_service.log_user_action(
        current_user.id, "logout", "auth", "", "", "", db=db
    )

    logger.info(f"User {current_user.username} logged out")

    return {"message": "Successfully logged out"}
