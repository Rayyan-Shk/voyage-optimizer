from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from src.data.database import get_db
from src.services.cache_service import cache_service
from src.core.config import settings


# Security
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Get current user from JWT token.
    For demonstration purposes, this is simplified.
    In production, implement proper JWT validation.
    """
    if not credentials and not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # In debug mode, return mock user
    if settings.debug:
        return {
            "user_id": "demo_user",
            "username": "demo",
            "permissions": ["read", "write"]
        }
    
    # In production, validate JWT token here
    # token = credentials.credentials
    # user = validate_jwt_token(token)
    # return user
    
    return {
        "user_id": "authenticated_user",
        "username": "user",
        "permissions": ["read", "write"]
    }


def get_cache_service():
    """Get cache service instance."""
    return cache_service


def get_database_session(db: Session = Depends(get_db)):
    """Get database session."""
    return db 