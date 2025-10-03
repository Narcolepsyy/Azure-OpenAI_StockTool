"""
Shared connection pool manager for optimized HTTP requests across the application.
This provides connection pooling to reduce latency and improve performance for API calls.
"""
import logging
import aiohttp
import requests
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class ConnectionPoolManager:
    """Manages shared HTTP connection pools for both async and sync requests."""
    
    _async_session: Optional[aiohttp.ClientSession] = None
    _sync_session: Optional[requests.Session] = None
    
    @classmethod
    async def get_async_session(cls) -> aiohttp.ClientSession:
        """Get or create shared async HTTP session with connection pooling."""
        if cls._async_session is None or cls._async_session.closed:
            # Configure connection pool for optimal performance
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=20,  # Max connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=60,
                enable_cleanup_closed=True,
                force_close=False,
                ssl=False,  # Allow reuse of SSL connections
            )
            
            # Configure timeouts
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            
            # Create session with optimized settings
            cls._async_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                trust_env=True,  # Respect proxy settings
                auto_decompress=True,
            )
            
        return cls._async_session
    
    @classmethod
    def get_sync_session(cls) -> requests.Session:
        """Get or create shared sync HTTP session with connection pooling."""
        if cls._sync_session is None:
            cls._sync_session = requests.Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                backoff_factor=0.3,
                respect_retry_after_header=True
            )
            
            # Configure connection pool adapters
            adapter = HTTPAdapter(
                pool_connections=20,  # Number of connection pools
                pool_maxsize=100,     # Max connections in pool
                max_retries=retry_strategy,
                pool_block=False
            )
            
            cls._sync_session.mount("http://", adapter)
            cls._sync_session.mount("https://", adapter)
            
            # Set default headers
            cls._sync_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
        return cls._sync_session
    
    @classmethod
    async def close_async_session(cls):
        """Close the async session and cleanup resources."""
        if cls._async_session and not cls._async_session.closed:
            await cls._async_session.close()
            cls._async_session = None
    
    @classmethod
    def close_sync_session(cls):
        """Close the sync session and cleanup resources."""
        if cls._sync_session:
            cls._sync_session.close()
            cls._sync_session = None
    
    @classmethod
    async def cleanup(cls):
        """Cleanup all connection pools."""
        await cls.close_async_session()
        cls.close_sync_session()

# Global instance for easy access
connection_pool = ConnectionPoolManager()