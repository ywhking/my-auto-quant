"""Custom exceptions for trader_initiator module."""


class ValidationError(Exception):
    r"""Raised when input parameters fail validation.

    This exception is raised when any of the trading parameters are invalid:
    - Stock code format doesn't match [0-9]{6}\.[A-Z]{2}
    - Action is not "buy" or "sell"
    - Price is not positive
    - Number is not positive
    """

    pass


class OrderFailedError(Exception):
    """Raised when the order execution fails at the executor level.

    This exception is raised when the proxy returns an error response
    indicating that the order could not be executed by the executor.
    The error message from the proxy is included in the exception.
    """

    pass
