"""Tests for Pydantic models in trader_executor."""

import pytest

from trader_executor.models import (
    ExecutionResult,
    ExecutorConfigModel,
    OrderCallbackResult,
    OrderData,
    TradingMessage,
)


class TestTradingMessage:
    """Test cases for TradingMessage model."""

    def test_valid_trading_message_buy(self) -> None:
        """Test creating a valid buy trading message."""
        msg = TradingMessage(stock="000001.SH", action="buy", price=19.60, number=1000)
        assert msg.stock == "000001.SH"
        assert msg.action == "buy"
        assert msg.price == 19.60
        assert msg.number == 1000

    def test_valid_trading_message_sell(self) -> None:
        """Test creating a valid sell trading message."""
        msg = TradingMessage(stock="600000.SH", action="sell", price=20.50, number=500)
        assert msg.stock == "600000.SH"
        assert msg.action == "sell"
        assert msg.price == 20.50
        assert msg.number == 500

    def test_invalid_stock_code_format(self) -> None:
        """Test validation of invalid stock code format."""
        with pytest.raises(ValueError) as exc_info:
            TradingMessage(stock="invalid", action="buy", price=19.60, number=1000)
        assert "Invalid stock code" in str(exc_info.value)

    def test_invalid_stock_code_wrong_digits(self) -> None:
        """Test validation of stock code with wrong number of digits."""
        with pytest.raises(ValueError) as exc_info:
            TradingMessage(stock="60000.SH", action="buy", price=19.60, number=1000)
        assert "Invalid stock code" in str(exc_info.value)

    def test_invalid_action(self) -> None:
        """Test validation of invalid action."""
        with pytest.raises(ValueError) as exc_info:
            TradingMessage(stock="000001.SH", action="hold", price=19.60, number=1000)
        assert "Input should be 'buy' or 'sell'" in str(exc_info.value)

    def test_invalid_price_negative(self) -> None:
        """Test validation of negative price."""
        with pytest.raises(ValueError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=-10.0, number=1000)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_invalid_price_zero(self) -> None:
        """Test validation of zero price."""
        with pytest.raises(ValueError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=0, number=1000)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_invalid_number_negative(self) -> None:
        """Test validation of negative number."""
        with pytest.raises(ValueError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=19.60, number=-100)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_invalid_number_zero(self) -> None:
        """Test validation of zero number."""
        with pytest.raises(ValueError) as exc_info:
            TradingMessage(stock="000001.SH", action="buy", price=19.60, number=0)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_valid_stock_codes_different_exchanges(self) -> None:
        """Test validation of valid stock codes from different exchanges."""
        valid_codes = [
            "600000.SH",  # Shanghai
            "000001.SZ",  # Shenzhen
            "300001.SZ",  # ChiNext
        ]
        for code in valid_codes:
            msg = TradingMessage(stock=code, action="buy", price=19.60, number=1000)
            assert msg.stock == code


class TestExecutionResult:
    """Test cases for ExecutionResult model."""

    def test_success_execution_result(self) -> None:
        """Test creating a successful execution result."""
        data = {"stock": "000001.SH", "action": "buy", "price": 19.60, "number": 1000}
        result = ExecutionResult(status="success", order_id="123456", data=data)
        assert result.status == "success"
        assert result.order_id == "123456"
        assert result.data == data
        assert result.message is None

    def test_error_execution_result(self) -> None:
        """Test creating an error execution result."""
        result = ExecutionResult(
            status="error", order_id=None, message="Insufficient funds"
        )
        assert result.status == "error"
        assert result.order_id is None
        assert result.message == "Insufficient funds"
        assert result.data is None

    def test_invalid_status(self) -> None:
        """Test validation of invalid status."""
        with pytest.raises(ValueError) as exc_info:
            ExecutionResult(status="invalid", order_id="123456")
        assert "Input should be 'success' or 'error'" in str(exc_info.value)


class TestOrderData:
    """Test cases for OrderData model."""

    def test_valid_order_data_buy(self) -> None:
        """Test creating valid buy order data."""
        data = OrderData(stock="000001.SH", action="buy", price=19.60, number=1000)
        assert data.stock == "000001.SH"
        assert data.action == "buy"
        assert data.price == 19.60
        assert data.number == 1000

    def test_valid_order_data_sell(self) -> None:
        """Test creating valid sell order data."""
        data = OrderData(stock="600000.SH", action="sell", price=20.50, number=500)
        assert data.stock == "600000.SH"
        assert data.action == "sell"
        assert data.price == 20.50
        assert data.number == 500


class TestOrderCallbackResult:
    """Test cases for OrderCallbackResult model."""

    def test_order_callback_result_with_status(self) -> None:
        """Test creating order callback result with status."""
        result = OrderCallbackResult(
            order_id="123456", order_status=53, status_msg="Order executed"
        )
        assert result.order_id == "123456"
        assert result.order_status == 53
        assert result.status_msg == "Order executed"
        assert result.traded_volume is None
        assert result.traded_price is None

    def test_order_callback_result_with_trade(self) -> None:
        """Test creating order callback result with trade data."""
        result = OrderCallbackResult(
            order_id="123456",
            traded_volume=1000,
            traded_price=19.60,
        )
        assert result.order_id == "123456"
        assert result.traded_volume == 1000
        assert result.traded_price == 19.60
        assert result.order_status is None
        assert result.status_msg is None

    def test_order_callback_result_with_error(self) -> None:
        """Test creating order callback result with error."""
        result = OrderCallbackResult(order_id="123456", status_msg="Insufficient funds")
        assert result.order_id == "123456"
        assert result.status_msg == "Insufficient funds"


class TestExecutorConfigModel:
    """Test cases for ExecutorConfigModel model."""

    def test_valid_executor_config(self) -> None:
        """Test creating a valid executor configuration."""
        config = ExecutorConfigModel(
            proxy={"host": "localhost", "port": 8000},
            auth={"username": "executor", "password": "password"},
            qmt={"account_id": "123456", "password": "qmt_password"},
            connection={"heartbeat_interval": 30},
            trading={"lot_size": 100},
            logging={"level": "INFO"},
        )
        assert config.proxy["host"] == "localhost"
        assert config.auth["username"] == "executor"
        assert config.qmt["account_id"] == "123456"
        assert config.connection["heartbeat_interval"] == 30
        assert config.trading["lot_size"] == 100
        assert config.logging["level"] == "INFO"

    def test_executor_config_model_dump(self) -> None:
        """Test dumping executor configuration to dict."""
        config = ExecutorConfigModel(
            proxy={"host": "localhost", "port": 8000},
            auth={"username": "executor", "password": "password"},
            qmt={"account_id": "123456", "password": "qmt_password"},
            connection={"heartbeat_interval": 30},
            trading={"lot_size": 100},
            logging={"level": "INFO"},
        )
        dumped = config.model_dump()
        assert isinstance(dumped, dict)
        assert "proxy" in dumped
        assert "auth" in dumped
        assert "qmt" in dumped
