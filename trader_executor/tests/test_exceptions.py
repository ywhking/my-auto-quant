"""Tests for custom exceptions in trader_executor."""

import pytest

from trader_executor.exceptions import (
    QMTConnectionError,
    QMTError,
    QMTExecutionError,
    QMTValidationError,
)


class TestQMTError:
    """Test cases for QMTError exception."""

    def test_qmt_error_creation(self) -> None:
        """Test creating QMTError with a message."""
        msg = "Base QMT error"
        exc = QMTError(msg)

        assert isinstance(exc, Exception)
        assert isinstance(exc, QMTError)
        assert str(exc) == msg

    def test_qmt_error_can_be_raised(self) -> None:
        """Test that QMTError can be raised and caught."""
        msg = "Test QMT error"

        with pytest.raises(QMTError) as exc_info:
            raise QMTError(msg)

        assert str(exc_info.value) == msg

    def test_qmt_error_inheritance(self) -> None:
        """Test that QMTError inherits from Exception."""
        exc = QMTError("test")
        assert isinstance(exc, Exception)


class TestQMTConnectionError:
    """Test cases for QMTConnectionError exception."""

    def test_qmt_connection_error_creation(self) -> None:
        """Test creating QMTConnectionError with a message."""
        msg = "Failed to connect to QMT"
        exc = QMTConnectionError(msg)

        assert isinstance(exc, Exception)
        assert isinstance(exc, QMTError)
        assert isinstance(exc, QMTConnectionError)
        assert str(exc) == msg

    def test_qmt_connection_error_can_be_raised(self) -> None:
        """Test that QMTConnectionError can be raised and caught."""
        msg = "QMT connection lost"

        with pytest.raises(QMTConnectionError) as exc_info:
            raise QMTConnectionError(msg)

        assert str(exc_info.value) == msg

    def test_qmt_connection_error_inheritance(self) -> None:
        """Test that QMTConnectionError inherits from QMTError."""
        exc = QMTConnectionError("test")
        assert isinstance(exc, QMTError)
        assert isinstance(exc, Exception)


class TestQMTExecutionError:
    """Test cases for QMTExecutionError exception."""

    def test_qmt_execution_error_creation(self) -> None:
        """Test creating QMTExecutionError with a message."""
        msg = "Order execution failed"
        exc = QMTExecutionError(msg)

        assert isinstance(exc, Exception)
        assert isinstance(exc, QMTError)
        assert isinstance(exc, QMTExecutionError)
        assert str(exc) == msg

    def test_qmt_execution_error_can_be_raised(self) -> None:
        """Test that QMTExecutionError can be raised and caught."""
        msg = "Insufficient funds"

        with pytest.raises(QMTExecutionError) as exc_info:
            raise QMTExecutionError(msg)

        assert str(exc_info.value) == msg

    def test_qmt_execution_error_inheritance(self) -> None:
        """Test that QMTExecutionError inherits from QMTError."""
        exc = QMTExecutionError("test")
        assert isinstance(exc, QMTError)
        assert isinstance(exc, Exception)


class TestQMTValidationError:
    """Test cases for QMTValidationError exception."""

    def test_qmt_validation_error_creation(self) -> None:
        """Test creating QMTValidationError with a message."""
        msg = "Invalid stock code format"
        exc = QMTValidationError(msg)

        assert isinstance(exc, Exception)
        assert isinstance(exc, QMTError)
        assert isinstance(exc, QMTValidationError)
        assert str(exc) == msg

    def test_qmt_validation_error_can_be_raised(self) -> None:
        """Test that QMTValidationError can be raised and caught."""
        msg = "Invalid action parameter"

        with pytest.raises(QMTValidationError) as exc_info:
            raise QMTValidationError(msg)

        assert str(exc_info.value) == msg

    def test_qmt_validation_error_inheritance(self) -> None:
        """Test that QMTValidationError inherits from QMTError."""
        exc = QMTValidationError("test")
        assert isinstance(exc, QMTError)
        assert isinstance(exc, Exception)
