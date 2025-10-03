"""
Session management and cleanup utilities to prevent memory leaks.
"""
import asyncio
import logging
import atexit
from typing import Set
import aiohttp

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages aiohttp sessions and ensures proper cleanup."""
    
    def __init__(self):
        self._sessions: Set[aiohttp.ClientSession] = set()
        self._closed = False
        
        # Register cleanup on exit
        atexit.register(self.cleanup_sync)
    
    def register_session(self, session: aiohttp.ClientSession):
        """Register a session for cleanup tracking."""
        if not self._closed:
            self._sessions.add(session)
    
    def unregister_session(self, session: aiohttp.ClientSession):
        """Unregister a session (when manually closed)."""
        self._sessions.discard(session)
    
    async def cleanup_all(self):
        """Async cleanup of all registered sessions."""
        if self._closed:
            return
            
        self._closed = True
        cleanup_tasks = []
        
        for session in list(self._sessions):
            if not session.closed:
                cleanup_tasks.append(session.close())
        
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                logger.info(f"Cleaned up {len(cleanup_tasks)} sessions")
            except Exception as e:
                logger.warning(f"Error during session cleanup: {e}")
        
        self._sessions.clear()
    
    def cleanup_sync(self):
        """Synchronous cleanup for atexit handler."""
        if self._closed or not self._sessions:
            return
        
        try:
            # Try to get current event loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create one for cleanup
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.cleanup_all())
            finally:
                loop.close()
        else:
            # There's a running loop, schedule cleanup
            asyncio.create_task(self.cleanup_all())

# Global session manager instance
session_manager = SessionManager()

def register_session(session: aiohttp.ClientSession):
    """Register a session for cleanup."""
    session_manager.register_session(session)

def unregister_session(session: aiohttp.ClientSession):
    """Unregister a session."""
    session_manager.unregister_session(session)

async def cleanup_all_sessions():
    """Cleanup all registered sessions."""
    await session_manager.cleanup_all()

# Enhanced session creation with automatic registration
def create_managed_session(**kwargs) -> aiohttp.ClientSession:
    """Create a managed session that will be automatically cleaned up."""
    session = aiohttp.ClientSession(**kwargs)
    register_session(session)
    return session