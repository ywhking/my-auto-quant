"""Unit tests for qmt_proxy models module."""

import pytest
from pydantic import ValidationError

from qmt_proxy.models import (
    ExecutorNotConnectedResponse,
    ErrorResponse,
    ExecutionResult,
    TokenResponse,
    TradingMessage,
    User,
    UserConfig,
)


class TestUser:
    """Test cases for User model."""

    def test_valid_user(self) -> None:
        """Test creating a valid User instance."""
        user = User(name="initiator", password="password123", role="initiator")
        assert user.name == "initiator"
        assert user.password == "password123"
        assert user.role == "initiator"


class TestUserConfig:
    """Test cases for UserConfig model."""

    def test_valid_user_config(self) -> None:
        """Test creating a valid UserConfig instance."""
        config = UserConfig(
            users=[
                User(name="initiator", password="pass1", role="initiator"),
                User(name="executor", password="pass2", role="executor"),
            ]
        )
        assert len(config.users) == 2
        assert config.users[0].name == "initiator"
        assert config.users[1].name == "executor"


class TestTokenResponse:
    """Test cases for TokenResponse model."""

    def test_valid_token_response(self) -> None:
        """Test creating a valid TokenResponse instance."""
        response = TokenResponse(token="abc-123-def-456")
        assert response.token == "abc-123-def-456"


class TestErrorResponse:
    """Test cases for ErrorResponse model."""

    def test_valid_error_response(self) -> None:
        """Test creating a valid ErrorResponse instance."""
        response = ErrorResponse(error="Invalid credentials")
        assert response.error == "Invalid credentials"


class TestTradingMessage:
    """Test cases for TradingMessage model."""

    def test_valid_trading_message_buy(self) -> None:
        """Test creating a valid TradingMessage for buy action."""
        message = TradingMessage(
            stock="000001.SH", action="buy", price=20.00, number=1000
        )
        assert message.stock == "000001.SH"
        assert message.action == "buy"
        assert message.price == 20.00
        assert message.number == 1000

    def test_valid_trading_message_sell(self) -> None:
        """Test creating a valid TradingMessage for sell action."""
        message = TradingMessage(
            stock="600000.SH", action="sell", price=15.50, number=500
        )
        assert message.stock == "600000.SH"
        assert message.action == "sell"
        assert message.price == 15.50
        assert message.number == 500

    def test_invalid_stock_code_format(self) -> None:
        """Test TradingMessage with invalid stock code format."""
        with pytest.raises(ValidationError) as exc_info:
            TradingMessage(stock="invalid", action="buy", price=20.00, number=1000)
        assert "Invalid stock code" in str(exc_info.value)

    def test_stock_code_wrong_format(self) -> None:
        """Test TradingMessage with wrong stock code format."""
        with pytest.raises(ValidationError) as exc_info:
            TradingMessage(stock="600000", action="buy", price=20.00, number=1000)
        assert "Invalid stock code" in str(exc_info.value)

    def test_invalid_action(self) -> None:
        """Test TradingMessage with invalid action."""
        with pytest.raises(ValidationError) as exc_info:
            TradingMessage(stock="000001.SH", action="hold", price=20.00, number=1000)
        assert "Input should be 'buy' or 'sell'" in str(exc_info.value)

    def test_negative_price(self) -> None:
        """Test TradingMessage with negative price."""
        with pytest.raises(ValidationError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=-10.00, number=1000)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_zero_price(self) -> None:
        """Test TradingMessage with zero price."""
        with pytest.raises(ValidationError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=0, number=1000)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_negative_number(self) -> None:
        """Test TradingMessage with negative quantity."""
        with pytest.raises(ValidationError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=20.00, number=-100)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_zero_number(self) -> None:
        """Test TradingMessage with zero quantity."""
        with pytest.raises(ValidationError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=20.00, number=0)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_valid_stock_code_shanghai(self) -> None:
        """Test valid Shanghai stock code formats."""
        TradingMessage(stock="600000.SH", action="buy", price=20.00, number=1000)
        TradingMessage(stock="000001.SH", action="buy", price=20.00, number=1000)
        TradingMessage(stock="300001.SH", action="buy", price=20.00, number=1000)

    def test_valid_stock_code_shenzhen(self) -> None:
        """Test valid Shenzhen stock code formats."""
        TradingMessage(stock="000001.SZ", action="buy", price=20.00, number=1000)
        TradingMessage(stock="002001.SZ", action="buy", price=20.00, number=1000)
        TradingMessage(stock="300001.SZ", action="buy", price=20.00, number=1000)


class TestExecutionResult:
    """Test cases for ExecutionResult model."""

    def test_success_execution_result(self) -> None:
        """Test creating a successful ExecutionResult."""
        result = ExecutionResult(
            status="success",
            data={
                "stock": "000001.SH",
                "action": "buy",
                "price": 19.60,
                "number": 1000,
            },
        )
        assert result.status == "success"
        assert result.data["stock"] == "000001.SH"
        assert result.message is None

    def test_error_execution_result(self) -> None:
        """Test creating an error ExecutionResult."""
        result = ExecutionResult(
            status="error",
            message="Order rejected",
            data={"stock": "000001.SH", "action": "buy", "price": 20, "number": 1000},
        )
        assert result.status == "error"
        assert result.message == "Order rejected"
        assert result.data is not None

    def test_execution_result_without_data(self) -> None:
        """Test ExecutionResult with no data field."""
        result = ExecutionResult(status="error", message="Connection failed")
        assert result.status == "error"
        assert result.message == "Connection failed"
        assert result.data is None


class TestExecutorNotConnectedResponse:
    """Test cases for ExecutorNotConnectedResponse model."""

    def test_executor_not_connected_response(self) -> None:
        """Test creating ExecutorNotConnectedResponse."""
        response = ExecutorNotConnectedResponse()
        assert response.status == "error"
        assert response.message == "Executor not connected"

    def test_executor_not_connected_response_model_dump(self) -> None:
        """Test model_dump returns correct format."""
        response = ExecutorNotConnectedResponse()
        dumped = response.model_dump()
        assert dumped == {
            "status": "error",
            "message": "Executor not connected",
        }
