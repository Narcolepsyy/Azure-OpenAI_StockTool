"""Authentication service for JWT token management."""
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import HTTPException, Response
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.core.config import (
    JWT_SECRET, JWT_ALG, ACCESS_TOKEN_EXPIRE_MINUTES, 
    REFRESH_TOKEN_EXPIRE_DAYS, REFRESH_COOKIE_NAME, 
    COOKIE_SECURE, COOKIE_DOMAIN, ADMIN_USERNAMES
)
from app.models.database import User, RefreshToken, PasswordReset

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)

def set_refresh_cookie(response: Response, token: str, expires_at: datetime):
    """Set refresh token as HTTP-only cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        expires=int(expires_at.timestamp()),
        domain=COOKIE_DOMAIN,
        path="/",
    )

def clear_refresh_cookie(response: Response):
    """Clear refresh token cookie."""
    response.delete_cookie(REFRESH_COOKIE_NAME, domain=COOKIE_DOMAIN, path="/")

def issue_refresh_token(db: Session, user_id: int) -> RefreshToken:
    """Issue a new refresh token for a user."""
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(user_id=user_id, token=token, expires_at=expires_at, revoked=False)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt

def revoke_refresh_token(db: Session, token: str):
    """Revoke a specific refresh token."""
    rt = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if rt:
        rt.revoked = True
        db.add(rt)
        db.commit()

def revoke_all_refresh_tokens(db: Session, user_id: int):
    """Revoke all refresh tokens for a user."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, 
        RefreshToken.revoked == False
    ).update({RefreshToken.revoked: True})
    db.commit()

def verify_access_token(token: str, db: Session) -> User:
    """Verify an access token and return the user."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        uid = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).get(uid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def is_admin_user(user: User) -> bool:
    """Check if a user has admin privileges."""
    return (user.username or "").strip().lower() in ADMIN_USERNAMES

def create_password_reset_token(db: Session, user_id: int) -> str:
    """Create a password reset token."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    pr = PasswordReset(user_id=user_id, token=token, expires_at=expires_at, used=False)
    db.add(pr)
    db.commit()
    return token

def verify_password_reset_token(db: Session, token: str) -> Optional[User]:
    """Verify a password reset token and return the user."""
    pr = db.query(PasswordReset).filter(PasswordReset.token == token).first()
    if not pr or pr.used or pr.expires_at <= datetime.now(timezone.utc):
        return None
    
    user = db.query(User).get(pr.user_id)
    if user:
        pr.used = True
        db.add(pr)
        db.commit()
    return user
