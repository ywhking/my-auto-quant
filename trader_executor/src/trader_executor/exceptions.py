"""Custom exceptions for trader_executor module."""


class QMTError(Exception):
    """Base exception for all QMT-related errors.

    This is the parent class for all custom exceptions in the trader_executor
    module. Specific exception types inherit from this class for easier error
    handling and categorization.
    """

    pass


class QMTConnectionError(QMTError):
    """Raised when connection to QMT client fails or is lost.

    This exception is raised when:
    - Initial connection to QMT client fails
    - Connection to QMT client is lost during operation
    - Reconnection attempts fail after maximum retries
    """

    pass


class QMTExecutionError(QMTError):
    """Raised when order execution fails at QMT client level.

    This exception is raised when the QMT client returns an error during
    order execution, such as:
    - Insufficient funds
    - Insufficient position
    - Market closed
    - Price out of valid range
    - Order rejected by QMT

    The error message from QMT is included in the exception for detailed
    troubleshooting.
    """

    pass


class QMTValidationError(QMTError):
    r"""Raised when order parameters fail validation.

    This exception is raised when trading parameters are invalid before
    submission to QMT:
    - Stock code format doesn't match [0-9]{6}\.[A-Z]{2}
    - Action is not "buy" or "sell"
    - Price is not positive
    - Number is not positive
    - Quantity is not a multiple of lot size
    """

    pass
