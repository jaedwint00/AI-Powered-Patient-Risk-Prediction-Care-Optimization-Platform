"""
Authentication and authorization service for the AI-Powered Patient Risk
Prediction platform.

Provides JWT-based authentication, user management, role-based access control,
and HIPAA-compliant audit logging functionality.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from loguru import logger

from config.settings import settings
from app.database.connection import get_database, DatabaseManager


class TokenData(BaseModel):
    """JWT token data model."""

    user_id: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    """User creation request model."""

    username: str
    email: str
    password: str
    role: str = "physician"  # physician, nurse, admin


class User(BaseModel):
    """User model for authentication."""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class AuthService:
    """Authentication and authorization service."""

    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.security = HTTPBearer()

    def verify_password(
            self,
            plain_password: str,
            hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, settings.secret_key, algorithm=settings.algorithm
        )

        return encoded_jwt

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, settings.secret_key, algorithms=[settings.algorithm]
            )
            user_id = payload.get("sub")
            role = payload.get("role")

            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return TokenData(user_id=user_id, role=role)

        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    async def create_user(
            self,
            user_create: UserCreate,
            db: DatabaseManager) -> User:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = await db.execute_query(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                [user_create.username, user_create.email],
            )

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this username or email already exists",
                )

            # Hash password
            hashed_password = self.get_password_hash(user_create.password)

            # Create user
            await db.execute_query(
                """
                INSERT INTO users (username, email, password_hash, role,
                                 is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                [
                    user_create.username,
                    user_create.email,
                    hashed_password,
                    user_create.role,
                    True,
                    datetime.utcnow(),
                ],
            )

            # Get created user
            user_result = await db.execute_query(
                "SELECT * FROM users WHERE username = ?", [user_create.username]
            )

            if not user_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user",
                )

            user_data = user_result[0]

            logger.info(f"Created user: {user_create.username}")

            return User(
                id=user_data[0],
                username=user_data[1],
                email=user_data[2],
                role=user_data[4],
                is_active=user_data[5],
                created_at=user_data[6],
                last_login=user_data[7],
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            ) from e

    async def authenticate_user(
        self, username: str, password: str, db: DatabaseManager
    ) -> Optional[User]:
        """Authenticate user credentials"""
        try:
            user_result = await db.execute_query(
                "SELECT * FROM users WHERE username = ? AND is_active = true",
                [username],
            )

            if not user_result:
                return None

            user_data = user_result[0]
            hashed_password = user_data[3]

            if not self.verify_password(password, hashed_password):
                return None

            # Update last login
            await db.execute_query(
                "UPDATE users SET last_login = ? WHERE id = ?",
                [datetime.utcnow(), user_data[0]],
            )

            return User(
                id=user_data[0],
                username=user_data[1],
                email=user_data[2],
                role=user_data[4],
                is_active=user_data[5],
                created_at=user_data[6],
                last_login=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
        db: DatabaseManager = Depends(get_database),
    ) -> User:
        """Get current authenticated user"""
        token_data = self.verify_token(credentials.credentials)

        user_result = await db.execute_query(
            "SELECT * FROM users WHERE id = ? AND is_active = true",
            [token_data.user_id],
        )

        if not user_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_data = user_result[0]

        return User(
            id=user_data[0],
            username=user_data[1],
            email=user_data[2],
            role=user_data[4],
            is_active=user_data[5],
            created_at=user_data[6],
            last_login=user_data[7],
        )

    def require_role(self, required_role: str):
        """Decorator to require specific role"""

        def role_checker(current_user: User = Depends(self.get_current_user)):
            if current_user.role not in (required_role, "admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            return current_user

        return role_checker

    async def create_tables(self, db: DatabaseManager):
        """Create user-related tables"""
        try:
            # Users table
            await db.execute_query(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR UNIQUE NOT NULL,
                    email VARCHAR UNIQUE NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    role VARCHAR NOT NULL DEFAULT 'physician',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """
            )

            # User sessions table for tracking
            await db.execute_query(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_token VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
            )

            # Audit log for HIPAA compliance
            await db.execute_query(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    action VARCHAR NOT NULL,
                    resource VARCHAR,
                    resource_id VARCHAR,
                    ip_address VARCHAR,
                    user_agent VARCHAR,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
            )

            logger.info("Authentication tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create authentication tables: {e}")
            raise

    async def log_user_action(
        self,
        user_id: int,
        action: str,
        resource: str = "",
        resource_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        db: Optional[DatabaseManager] = None,
    ):
        """Log user action for HIPAA compliance"""
        try:
            if db:
                await db.execute_query(
                    """
                    INSERT INTO audit_log (
                        user_id, action, resource, resource_id,
                        ip_address, user_agent, timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    [
                        user_id,
                        action,
                        resource,
                        resource_id,
                        ip_address,
                        user_agent,
                        datetime.utcnow(),
                    ],
                )

        except Exception as e:
            logger.error(f"Failed to log user action: {e}")


# Global auth service instance
auth_service = AuthService()
