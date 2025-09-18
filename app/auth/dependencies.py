"""Authentication dependencies for FastAPI endpoints."""
from typing import Optional
from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db, User
from app.auth.service import verify_access_token, is_admin_user

def get_current_user(
    authorization: Optional[str] = Header(default=None), 
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token."""
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    
    return verify_access_token(token, db)

def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Get current user and verify admin privileges."""
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="admin only")
    return user
