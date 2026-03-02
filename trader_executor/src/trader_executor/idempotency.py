"""Idempotency handler for trader_executor.

Prevents duplicate order execution by caching order results
and checking for duplicate order IDs.
"""

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IdempotencyHandler:
    """Handles order idempotency.

    Caches order results by order_id to prevent duplicate execution.
    Uses in-memory storage with TTL-based expiration.

    For production use, consider replacing with Redis-backed storage.
    """

    def __init__(self, ttl: int = 86400) -> None:
        """Initialize IdempotencyHandler.

        Args:
            ttl: Time-to-live for cached results in seconds (default: 24 hours)
        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("IdempotencyHandler cleanup task started")

    async def stop(self) -> None:
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("IdempotencyHandler cleanup task stopped")

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(3600)  # Clean up every hour
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        now = time.time()
        expired_keys = [
            key for key, data in self._cache.items()
            if now - data["timestamp"] > self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired idempotency records")

    async def check_and_set(
        self, order_id: str, result: dict[str, Any] | None = None
    ) -> tuple[bool, dict[str, Any] | None]:
        """Check if order was already processed, optionally cache result.

        Args:
            order_id: Unique order identifier
            result: Optional result to cache if order is new

        Returns:
            Tuple of (is_duplicate: bool, cached_result: dict | None)
            - If is_duplicate is True, cached_result contains the original result
            - If is_duplicate is False, cached_result is None
        """
        async with self._lock:
            if order_id in self._cache:
                cached = self._cache[order_id]
                if time.time() - cached["timestamp"] <= self._ttl:
                    logger.info(f"Duplicate order detected: order_id={order_id}")
                    return True, cached.get("result")
                else:
                    # Expired, remove it
                    del self._cache[order_id]

            # New order, cache result if provided
            if result is not None:
                self._cache[order_id] = {
                    "result": result,
                    "timestamp": time.time(),
                }
                logger.debug(f"Cached order result: order_id={order_id}")

            return False, None

    async def set_result(self, order_id: str, result: dict[str, Any]) -> None:
        """Cache order result after execution.

        Args:
            order_id: Unique order identifier
            result: Execution result to cache
        """
        async with self._lock:
            self._cache[order_id] = {
                "result": result,
                "timestamp": time.time(),
            }
            logger.debug(f"Set order result: order_id={order_id}")

    async def get_result(self, order_id: str) -> dict[str, Any] | None:
        """Get cached result for an order.

        Args:
            order_id: Unique order identifier

        Returns:
            Cached result if found and not expired, None otherwise
        """
        async with self._lock:
            if order_id in self._cache:
                cached = self._cache[order_id]
                if time.time() - cached["timestamp"] <= self._ttl:
                    return cached.get("result")
                else:
                    del self._cache[order_id]
            return None

    async def clear(self) -> None:
        """Clear all cached results."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} idempotency records")

    def get_cache_size(self) -> int:
        """Get current cache size.

        Returns:
            Number of cached entries
        """
        return len(self._cache)
