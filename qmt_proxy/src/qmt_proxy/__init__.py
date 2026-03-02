"""QMT Proxy - Trading message relay system.

This module provides a WebSocket-based proxy that forwards trading messages
between the Trading Initiator and Trading Executor.

Main components:
- FastAPI application with /auth and /ws endpoints
- Token-based authentication
- Role-based connection management
- Message forwarding between initiator and executor
"""

__version__ = "0.1.0"

# Import custom exceptions for package-level access
from .exceptions import (
    AuthenticationError,
    ConnectionManagerError,
    InvalidTokenError,
)

__all__ = [
    "AuthenticationError",
    "ConnectionManagerError",
    "InvalidTokenError",
]
