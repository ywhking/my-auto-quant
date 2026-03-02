"""Custom exceptions for QMT Proxy module."""


class AuthenticationError(Exception):
    """Raised when authentication fails.

    This exception is raised when user credentials are invalid
    or when there's an error during the authentication process.
    """

    pass


class InvalidTokenError(Exception):
    """Raised when a token is invalid or expired.

    This exception is raised when:
    - Token format is invalid
    - Token is not found in the token storage
    - Token has expired
    """

    pass


class ConnectionManagerError(Exception):
    """Raised when connection management operations fail.

    This exception is raised when:
    - Failed to add or remove a connection
    - Failed to send a message to a connection
    - Connection state is inconsistent
    """

    pass
