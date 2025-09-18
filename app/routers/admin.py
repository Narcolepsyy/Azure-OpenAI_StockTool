"""Admin API routes for system administration."""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, User, Log
from app.models.schemas import AdminLogsResponse
from app.auth.dependencies import get_current_admin
from app.services.rag_service import rag_reindex

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/logs", response_model=AdminLogsResponse)
def admin_logs(
    limit: int = 50,
    offset: int = 0,
    user: Optional[str] = None,
    action: Optional[str] = None,
    conversation_id: Optional[str] = None,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get system logs for admin users."""
    q = db.query(Log)

    if user:
        # Filter by username
        q = q.join(User, Log.user_id == User.id).filter(User.username.ilike(f"%{user}%"))
    if action:
        q = q.filter(Log.action == action)
    if conversation_id:
        q = q.filter(Log.conversation_id == conversation_id)

    total = q.count()
    rows = q.order_by(Log.created_at.desc()).offset(max(0, int(offset))).limit(max(1, min(500, int(limit)))).all()

    items = []
    for r in rows:
        try:
            u = db.query(User).get(r.user_id)
            items.append({
                "id": r.id,
                "user_id": r.user_id,
                "username": u.username if u else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "action": r.action,
                "conversation_id": r.conversation_id,
                "prompt": r.prompt,
                "response": r.response,
                "tool_calls": r.tool_calls,
            })
        except Exception:
            continue

    return AdminLogsResponse(total=total, items=items)

@router.post("/rag/reindex", response_model=Dict[str, Any])
def admin_rag_reindex(
    payload: Optional[Dict[str, Any]] = None,
    _: User = Depends(get_current_admin)
):
    """Reindex the RAG knowledge base."""
    clear = True
    try:
        if isinstance(payload, dict) and "clear" in payload:
            clear = bool(payload.get("clear"))
    except Exception:
        clear = True

    res = rag_reindex(clear=clear)
    return {"ok": True, **(res or {})}
