"""WebSocket connection manager for QMT Proxy.

Manages active WebSocket connections and handles message forwarding
between initiator and executor roles.
"""

import logging
from typing import Final

from fastapi import WebSocket

from .exceptions import ConnectionManagerError

logger = logging.getLogger(__name__)

# Connection storage: maps role to active connection
_connections: dict[str, WebSocket] = {}

# Valid roles
ROLE_INITIATOR: Final = "initiator"
ROLE_EXECUTOR: Final = "executor"


class ConnectionManager:
    """Manages WebSocket connections and message routing.

    Provides methods to:
    - Add and remove connections by role
    - Send messages to specific roles
    - Check connection availability
    """

    @staticmethod
    async def connect(role: str, websocket: WebSocket) -> None:
        """Add a WebSocket connection for the specified role.

        Args:
            role: Connection role ('initiator' or 'executor')
            websocket: WebSocket connection instance

        Raises:
            ConnectionManagerError: If role is invalid or connection already exists
        """
        if role not in (ROLE_INITIATOR, ROLE_EXECUTOR):
            msg = f"Invalid role: {role}"
            logger.error(msg)
            raise ConnectionManagerError(msg)

        if role in _connections:
            msg = f"Connection already exists for role: {role}"
            logger.warning(msg)
            raise ConnectionManagerError(msg)

        _connections[role] = websocket
        logger.info(f"WebSocket connected for role: {role}")

    @staticmethod
    async def disconnect(role: str) -> None:
        """Remove a WebSocket connection for the specified role.

        Args:
            role: Connection role to disconnect
        """
        if role in _connections:
            del _connections[role]
            logger.info(f"WebSocket disconnected for role: {role}")

    @staticmethod
    async def send_to_executor(message: dict) -> None:
        """Send a message to the executor connection.

        Args:
            message: Message dict to send (will be JSON serialized)

        Raises:
            ConnectionManagerError: If executor is not connected
        """
        if ROLE_EXECUTOR not in _connections:
            msg = "Executor not connected"
            logger.warning(msg)
            raise ConnectionManagerError(msg)

        websocket = _connections[ROLE_EXECUTOR]
        try:
            import json

            await websocket.send_json(message)
            logger.debug(f"Message sent to executor: {message}")
        except Exception as e:
            msg = f"Failed to send message to executor: {e}"
            logger.error(msg)
            raise ConnectionManagerError(msg) from e

    @staticmethod
    async def send_to_initiator(message: dict) -> None:
        """Send a message to the initiator connection.

        Args:
            message: Message dict to send (will be JSON serialized)

        Raises:
            ConnectionManagerError: If initiator is not connected
        """
        if ROLE_INITIATOR not in _connections:
            msg = "Initiator not connected"
            logger.warning(msg)
            raise ConnectionManagerError(msg)

        websocket = _connections[ROLE_INITIATOR]
        try:
            import json

            await websocket.send_json(message)
            logger.debug(f"Message sent to initiator: {message}")
        except Exception as e:
            msg = f"Failed to send message to initiator: {e}"
            logger.error(msg)
            raise ConnectionManagerError(msg) from e

    @staticmethod
    def is_executor_connected() -> bool:
        """Check if executor is connected.

        Returns:
            True if executor is connected, False otherwise
        """
        return ROLE_EXECUTOR in _connections

    @staticmethod
    def is_initiator_connected() -> bool:
        """Check if initiator is connected.

        Returns:
            True if initiator is connected, False otherwise
        """
        return ROLE_INITIATOR in _connections

    @staticmethod
    def get_connection_count() -> int:
        """Get the total number of active connections.

        Returns:
            Number of active connections
        """
        return len(_connections)

    @staticmethod
    async def close_all_connections() -> None:
        """Close all WebSocket connections gracefully."""
        import asyncio

        close_tasks = []
        for role, websocket in list(_connections.items()):
            try:
                close_tasks.append(websocket.close())
                logger.info(f"Closing WebSocket connection for role: {role}")
            except Exception as e:
                logger.error(f"Error closing connection for {role}: {e}")

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        count = len(_connections)
        _connections.clear()
        logger.info(f"Closed and cleared {count} connections")
    def clear_all_connections() -> None:
        """Clear all connections (useful for testing)."""
        count = len(_connections)
        _connections.clear()
        logger.info(f"Cleared {count} connections")

    @staticmethod
    def get_connected_roles() -> list[str]:
        """Get list of currently connected roles.

        Returns:
            List of connected role names
        """
        return list(_connections.keys())
