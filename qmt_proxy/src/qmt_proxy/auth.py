"""Authentication module for QMT Proxy.

Handles token generation, validation, and role-based access control.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Final

from .exceptions import AuthenticationError, InvalidTokenError
from .models import User, UserConfig

logger = logging.getLogger(__name__)

# Token storage: maps token to (username, role)
_token_store: dict[str, tuple[str, str]] = {}

# Config path: from src/qmt_proxy/auth.py -> qmt_proxy/config/users.json
USERS_CONFIG_PATH: Final = Path(__file__).parent.parent.parent / "config" / "users.json"


def load_user_credentials() -> UserConfig:
    """Load user credentials from config/users.json.

    Returns:
        UserConfig: Configuration containing list of users

    Raises:
        AuthenticationError: If config file cannot be loaded or parsed
    """
    if not USERS_CONFIG_PATH.exists():
        msg = f"User config file not found: {USERS_CONFIG_PATH}"
        logger.error(msg)
        raise AuthenticationError(msg)

    try:
        with open(USERS_CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return UserConfig(**data)
    except (json.JSONDecodeError, OSError) as e:
        msg = f"Failed to load user config: {e}"
        logger.error(msg)
        raise AuthenticationError(msg) from e


def authenticate_user(username: str, password: str) -> str:
    """Authenticate user and generate token.

    Args:
        username: User name
        password: User password

    Returns:
        Token string for authenticated user

    Raises:
        AuthenticationError: If credentials are invalid
    """
    user_config = load_user_credentials()

    for user in user_config.users:
        if user.name == username and user.password == password:
            # Generate unique token
            token = str(uuid.uuid4())
            _token_store[token] = (username, user.role)
            logger.info(f"User '{username}' authenticated with role '{user.role}'")
            return token

    msg = f"Invalid credentials for user: {username}"
    logger.warning(msg)
    raise AuthenticationError(msg)


def validate_token(token: str) -> tuple[str, str]:
    """Validate token and return (username, role).

    Args:
        token: Token to validate

    Returns:
        Tuple of (username, role)

    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    if not token:
        raise InvalidTokenError("Token cannot be empty")

    if token in _token_store:
        username, role = _token_store[token]
        return username, role

    raise InvalidTokenError(f"Invalid or expired token: {token}")


def revoke_token(token: str) -> None:
    """Revoke a token.

    Args:
        token: Token to revoke
    """
    if token in _token_store:
        username, role = _token_store[token]
        del _token_store[token]
        logger.info(f"Token revoked for user: {username}")


def clear_all_tokens() -> None:
    """Clear all tokens (for testing)."""
    _token_store.clear()
    logger.debug("All tokens cleared")


def get_active_token_count() -> int:
    """Get count of active tokens.

    Returns:
        Number of active tokens
    """
    return len(_token_store)
