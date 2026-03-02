"""Tests for custom exceptions in trader_initiator."""

import pytest

from trader_initiator.exceptions import OrderFailedError, ValidationError


class TestValidationError:
    """Test cases for ValidationError exception."""

    def test_validation_error_creation(self) -> None:
        """Test creating ValidationError with a message."""
        msg = "Invalid stock code format"
        exc = ValidationError(msg)

        assert isinstance(exc, Exception)
        assert isinstance(exc, ValidationError)
        assert str(exc) == msg

    def test_validation_error_can_be_raised(self) -> None:
        """Test that ValidationError can be raised and caught."""
        msg = "Invalid action"

        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError(msg)

        assert str(exc_info.value) == msg

    def test_validation_error_inheritance(self) -> None:
        """Test that ValidationError inherits from Exception."""
        exc = ValidationError("test")
        assert isinstance(exc, Exception)


class TestOrderFailedError:
    """Test cases for OrderFailedError exception."""

    def test_order_failed_error_creation(self) -> None:
        """Test creating OrderFailedError with a message."""
        msg = "Executor not connected"
        exc = OrderFailedError(msg)

        assert isinstance(exc, Exception)
        assert isinstance(exc, OrderFailedError)
        assert str(exc) == msg

    def test_order_failed_error_can_be_raised(self) -> None:
        """Test that OrderFailedError can be raised and caught."""
        msg = "Order rejected by QMT"

        with pytest.raises(OrderFailedError) as exc_info:
            raise OrderFailedError(msg)

        assert str(exc_info.value) == msg

    def test_order_failed_error_inheritance(self) -> None:
        """Test that OrderFailedError inherits from Exception."""
        exc = OrderFailedError("test")
        assert isinstance(exc, Exception)
