"""Authentication API routes."""
from fastapi import APIRouter, HTTPException, Response, Cookie, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.models.database import get_db, User
from app.models.schemas import TokenResponse, RegisterRequest, PasswordResetRequest, PasswordResetApply
from app.auth.service import (
    hash_password, verify_password, create_access_token, 
    set_refresh_cookie, clear_refresh_cookie, issue_refresh_token,
    revoke_all_refresh_tokens, create_password_reset_token,
    verify_password_reset_token, is_admin_user
)
from app.auth.dependencies import get_current_user
from app.core.config import REFRESH_COOKIE_NAME
from app.models.database import RefreshToken

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Dict[str, Any])
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    username = (req.username or "").strip()
    if not username or not req.password:
        raise HTTPException(status_code=400, detail="username and password are required")
    
    # Check duplicate
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=409, detail="username already exists")
    
    user = User(username=username, email=req.email, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"id": user.id, "username": user.username, "email": user.email}

@router.post("/token", response_model=TokenResponse)
def login(
    response: Response, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """Login and get access token."""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid username or password")
    
    token = create_access_token({"sub": str(user.id), "username": user.username})
    
    # Issue refresh token cookie
    rt = issue_refresh_token(db, user.id)
    set_refresh_cookie(response, rt.token, rt.expires_at)
    
    return TokenResponse(
        access_token=token, 
        user={
            "id": user.id, 
            "username": user.username, 
            "email": user.email, 
            "is_admin": is_admin_user(user)
        }
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_token_endpoint(
    response: Response,
    refresh_token_cookie: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    refresh_token = refresh_token_cookie
    if not refresh_token:
        raise HTTPException(status_code=400, detail="missing refresh token")
    
    rt = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if not rt or rt.revoked or rt.expires_at <= db.execute("SELECT NOW()").scalar():
        raise HTTPException(status_code=401, detail="invalid or expired refresh token")
    
    user = db.query(User).get(rt.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    
    # Rotate refresh token
    rt.revoked = True
    db.add(rt)
    db.commit()
    
    new_rt = issue_refresh_token(db, user.id)
    set_refresh_cookie(response, new_rt.token, new_rt.expires_at)
    
    access = create_access_token({"sub": str(user.id), "username": user.username})
    
    return TokenResponse(
        access_token=access, 
        user={
            "id": user.id, 
            "username": user.username, 
            "email": user.email, 
            "is_admin": is_admin_user(user)
        }
    )

@router.post("/logout")
def logout(
    response: Response, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Logout and revoke refresh tokens."""
    clear_refresh_cookie(response)
    revoke_all_refresh_tokens(db, current_user.id)
    return {"ok": True}

@router.post("/request-password-reset", response_model=Dict[str, Any])
def request_password_reset(req: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request a password reset token."""
    user = db.query(User).filter(User.username == (req.username or "").strip()).first()
    if not user:
        return {"ok": True}  # Don't reveal if user exists
    
    token = create_password_reset_token(db, user.id)
    return {"ok": True, "reset_token": token}

@router.post("/reset-password", response_model=Dict[str, Any])
def reset_password(req: PasswordResetApply, db: Session = Depends(get_db)):
    """Reset password using reset token."""
    user = verify_password_reset_token(db, req.token)
    if not user:
        raise HTTPException(status_code=400, detail="invalid or expired reset token")
    
    user.password_hash = hash_password(req.new_password)
    revoke_all_refresh_tokens(db, user.id)
    
    db.add(user)
    db.commit()
    
    return {"ok": True}

@router.get("/me", response_model=Dict[str, Any])
def me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.id, 
        "username": current_user.username, 
        "email": current_user.email, 
        "is_admin": is_admin_user(current_user)
    }
