"""Tool usage logging for ML training data collection."""
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

# Log file path
LOG_DIR = Path("data")
LOG_FILE = LOG_DIR / "tool_usage_logs.jsonl"

# Ensure directory exists
LOG_DIR.mkdir(exist_ok=True, parents=True)


def log_tool_usage(
    query: str,
    tools_available: Set[str],
    tools_called: List[str],
    success: bool,
    execution_time: float,
    model: str,
    conversation_id: str,
    user_id: Optional[str] = None,
    error: Optional[str] = None,
    tool_results: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    Log tool usage for ML training data collection.
    
    Args:
        query: User query text
        tools_available: Set of tools that were offered to the AI
        tools_called: List of tools that the AI actually called
        success: Whether the request completed successfully
        execution_time: Total execution time in seconds
        model: Model used (e.g., "gpt-4o")
        conversation_id: Conversation ID
        user_id: User ID (optional, for privacy can be hashed)
        error: Error message if failed (optional)
        tool_results: Tool execution results (optional)
    """
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:500],  # Truncate long queries
            "query_length": len(query),
            "tools_available": sorted(list(tools_available)),
            "tools_called": tools_called,
            "num_tools_available": len(tools_available),
            "num_tools_called": len(tools_called),
            "success": success,
            "execution_time": round(execution_time, 2),
            "model": model,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "error": error,
        }
        
        # Add tool result metadata (not full results to save space)
        if tool_results:
            log_entry["tool_result_summary"] = [
                {
                    "name": tr.get("name"),
                    "has_result": "result" in tr,
                    "has_error": "error" in tr,
                }
                for tr in tool_results
            ]
        
        # Append to JSONL file
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        logger.debug(f"Logged tool usage: {len(tools_called)} calls from {len(tools_available)} available")
        
    except Exception as e:
        # Don't let logging failures break the main flow
        logger.error(f"Failed to log tool usage: {e}", exc_info=True)


def get_log_stats() -> Dict[str, Any]:
    """Get statistics about logged tool usage."""
    if not LOG_FILE.exists():
        return {"total_logs": 0, "error": "No logs found"}
    
    try:
        total = 0
        successes = 0
        failures = 0
        tools_called_count = {}
        total_time = 0.0
        
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                    total += 1
                    
                    if entry.get("success"):
                        successes += 1
                    else:
                        failures += 1
                    
                    total_time += entry.get("execution_time", 0)
                    
                    for tool in entry.get("tools_called", []):
                        tools_called_count[tool] = tools_called_count.get(tool, 0) + 1
                        
                except json.JSONDecodeError:
                    continue
        
        return {
            "total_logs": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round(successes / max(1, total) * 100, 1),
            "avg_execution_time": round(total_time / max(1, total), 2),
            "tools_called_count": tools_called_count,
            "log_file": str(LOG_FILE),
            "file_size_mb": round(LOG_FILE.stat().st_size / (1024 * 1024), 2),
        }
    
    except Exception as e:
        logger.error(f"Failed to get log stats: {e}")
        return {"error": str(e)}


def clear_logs(confirm: bool = False) -> bool:
    """
    Clear tool usage logs.
    
    Args:
        confirm: Must be True to actually clear logs (safety)
    
    Returns:
        True if cleared, False if not confirmed
    """
    if not confirm:
        logger.warning("clear_logs called without confirmation")
        return False
    
    try:
        if LOG_FILE.exists():
            # Backup before clearing
            backup_file = LOG_DIR / f"tool_usage_logs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            LOG_FILE.rename(backup_file)
            logger.info(f"Backed up logs to {backup_file}")
        
        # Create new empty file
        LOG_FILE.touch()
        logger.info("Cleared tool usage logs")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
        return False
