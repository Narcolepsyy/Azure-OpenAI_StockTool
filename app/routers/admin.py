"""Admin API routes for system administration."""
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, User, Log
from app.models.schemas import AdminLogsResponse
from app.auth.dependencies import get_current_admin
from app.services.rag_service import rag_reindex
from app.utils.circuit_breaker import get_all_circuit_breaker_stats
from app.utils.cache_manager import get_cache_manager
from app.utils.request_deduplication import get_deduplication_manager
from app.utils.performance_monitor import get_performance_monitor
from app.utils.memory_monitor import get_memory_monitor

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

@router.get("/circuit-breakers", response_model=Dict[str, Dict[str, Any]])
def admin_circuit_breakers(_: User = Depends(get_current_admin)):
    """Get circuit breaker statistics for monitoring external service health."""
    return get_all_circuit_breaker_stats()

@router.get("/cache-stats", response_model=Dict[str, Dict[str, Any]])
def admin_cache_stats(_: User = Depends(get_current_admin)):
    """Get cache statistics for all cache instances."""
    cache_manager = get_cache_manager()
    return cache_manager.get_all_stats()

@router.get("/cache-summary", response_model=Dict[str, Any])
def admin_cache_summary(_: User = Depends(get_current_admin)):
    """Get summary statistics across all caches."""
    cache_manager = get_cache_manager()
    return cache_manager.get_summary_stats()

@router.post("/cache/clear/{cache_type}")
def admin_clear_cache(
    cache_type: str,
    _: User = Depends(get_current_admin)
):
    """Clear a specific cache type."""
    from app.utils.cache_manager import CacheType
    
    try:
        cache_type_enum = CacheType(cache_type)
        cache_manager = get_cache_manager()
        success = cache_manager.clear_cache(cache_type_enum)
        return {"success": success, "cache_type": cache_type}
    except ValueError:
        return {"success": False, "error": f"Invalid cache type: {cache_type}"}

@router.post("/cache/clear-all")
def admin_clear_all_caches(_: User = Depends(get_current_admin)):
    """Clear all caches."""
    cache_manager = get_cache_manager()
    cache_manager.clear_all_caches()
    return {"success": True, "message": "All caches cleared"}

@router.get("/cache/health", response_model=Dict[str, Any])
def admin_cache_health(_: User = Depends(get_current_admin)):
    """Perform health check on all caches."""
    cache_manager = get_cache_manager()
    return cache_manager.health_check()

@router.get("/deduplication-stats", response_model=Dict[str, Any])
def admin_deduplication_stats(_: User = Depends(get_current_admin)):
    """Get request deduplication statistics."""
    dedup_manager = get_deduplication_manager()
    return dedup_manager.get_stats()

@router.get("/active-requests", response_model=Dict[str, Dict[str, Any]])
def admin_active_requests(_: User = Depends(get_current_admin)):
    """Get currently active deduplicated requests."""
    dedup_manager = get_deduplication_manager()
    return dedup_manager.get_active_requests()

@router.get("/recent-requests", response_model=Dict[str, Dict[str, Any]])
def admin_recent_requests(
    limit: int = 50,
    _: User = Depends(get_current_admin)
):
    """Get recent request information."""
    dedup_manager = get_deduplication_manager()
    return dedup_manager.get_recent_requests(limit=limit)

@router.post("/deduplication/clear-completed")
def admin_clear_completed_requests(_: User = Depends(get_current_admin)):
    """Clear completed request history."""
    dedup_manager = get_deduplication_manager()
    cleared_count = dedup_manager.clear_completed()
    return {"success": True, "cleared_count": cleared_count}

@router.get("/performance-stats", response_model=Dict[str, Any])
def admin_performance_stats(_: User = Depends(get_current_admin)):
    """Get performance monitoring statistics."""
    performance_monitor = get_performance_monitor()
    return performance_monitor.get_stats()

@router.get("/metrics/summary", response_model=Dict[str, Dict[str, Any]])
def admin_metrics_summary(_: User = Depends(get_current_admin)):
    """Get summary of all collected metrics."""
    performance_monitor = get_performance_monitor()
    return performance_monitor.metrics.get_all_summaries()

@router.get("/metrics/{metric_name}")
def admin_metric_details(
    metric_name: str,
    limit: Optional[int] = 100,
    _: User = Depends(get_current_admin)
):
    """Get detailed information about a specific metric."""
    performance_monitor = get_performance_monitor()
    
    # Get summary
    summary = performance_monitor.metrics.get_metric_summary(metric_name)
    if not summary:
        return {"error": f"Metric '{metric_name}' not found"}
    
    # Get recent points
    recent_points = performance_monitor.metrics.get_recent_points(
        name=metric_name,
        limit=limit
    )
    
    return {
        "summary": summary.to_dict(),
        "recent_points": recent_points,
        "point_count": len(recent_points)
    }

@router.post("/metrics/clear/{metric_name}")
def admin_clear_metric(
    metric_name: str,
    _: User = Depends(get_current_admin)
):
    """Clear a specific metric."""
    performance_monitor = get_performance_monitor()
    success = performance_monitor.metrics.clear_metric(metric_name)
    return {"success": success, "metric_name": metric_name}

@router.post("/metrics/clear-all")
def admin_clear_all_metrics(_: User = Depends(get_current_admin)):
    """Clear all metrics."""
    performance_monitor = get_performance_monitor()
    performance_monitor.metrics.clear_all_metrics()
    return {"success": True, "message": "All metrics cleared"}

@router.get("/system-health", response_model=Dict[str, Any])
def admin_system_health(_: User = Depends(get_current_admin)):
    """Get overall system health status."""
    cache_manager = get_cache_manager()
    dedup_manager = get_deduplication_manager()
    performance_monitor = get_performance_monitor()
    
    # Gather health data
    cache_health = cache_manager.health_check()
    cache_summary = cache_manager.get_summary_stats()
    dedup_stats = dedup_manager.get_stats()
    perf_stats = performance_monitor.get_stats()
    circuit_breakers = get_all_circuit_breaker_stats()
    
    # Calculate overall health
    issues = []
    if not cache_health.get("healthy", False):
        issues.extend(cache_health.get("issues", []))
    
    # Check for high failure rates in circuit breakers
    for cb_name, cb_stats in circuit_breakers.items():
        if cb_stats.get("failure_rate", 0) > 0.1:  # > 10% failure rate
            issues.append(f"High failure rate in {cb_name}: {cb_stats['failure_rate']:.2%}")
    
    # Check cache utilization
    if cache_summary.get("usage_percent", 0) > 90:
        issues.append(f"High cache utilization: {cache_summary['usage_percent']:.1f}%")
    
    overall_healthy = len(issues) == 0
    
    return {
        "healthy": overall_healthy,
        "issues": issues,
        "cache_health": cache_health,
        "cache_summary": cache_summary,
        "deduplication_stats": dedup_stats,
        "performance_stats": perf_stats,
        "circuit_breakers": circuit_breakers,
        "timestamp": datetime.now().isoformat(),
    }

@router.get("/memory-stats", response_model=Dict[str, Any])
def admin_memory_stats(_: User = Depends(get_current_admin)):
    """Get memory usage statistics and limits."""
    memory_monitor = get_memory_monitor()
    return memory_monitor.check_memory_limits()

@router.get("/memory-trends", response_model=Dict[str, Any])
def admin_memory_trends(
    minutes: int = 30,
    _: User = Depends(get_current_admin)
):
    """Get memory usage trends over time."""
    memory_monitor = get_memory_monitor()
    return memory_monitor.get_memory_trends(minutes=minutes)

@router.post("/memory/gc", response_model=Dict[str, Any])
def admin_force_gc(_: User = Depends(get_current_admin)):
    """Force garbage collection to free memory."""
    memory_monitor = get_memory_monitor()
    collected = memory_monitor.force_garbage_collection()
    return {
        "success": True,
        "objects_freed": collected,
        "timestamp": datetime.now().isoformat()
    }
