"""Pytest fixtures for trader_executor tests."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trader_executor.config import ExecutorConfig
from trader_executor.qmt_client import QMTClientWrapper


@pytest.fixture
def mock_config():
    """Create a mock ExecutorConfig for testing with allow_mock enabled."""
    config = ExecutorConfig()
    config._config_data["allow_mock"] = True
    return config


@pytest.fixture
def mock_qmt_client():
    """Create a mock QMTClientWrapper for testing."""
    with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
        client = QMTClientWrapper()
        client._connected = True
        client._subscribed = True
        client._account = MagicMock()
        client._callback = MagicMock()
        client._xt_trader = MagicMock()
        return client


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    websocket = AsyncMock()
    websocket.send = AsyncMock()
    websocket.recv = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_order():
    """Create a mock order object from QMT."""
    order = MagicMock()
    order.order_id = "123456"
    order.order_status = 53  # 全成
    order.status_msg = "Order executed"
    return order


@pytest.fixture
def mock_trade():
    """Create a mock trade object from QMT."""
    trade = MagicMock()
    trade.order_id = "123456"
    trade.traded_volume = 1000
    trade.traded_price = 19.60
    return trade


@pytest.fixture
def mock_order_error():
    """Create a mock order error object from QMT."""
    error = MagicMock()
    error.order_id = "123456"
    error.error_msg = "Insufficient funds"
    return error


@pytest.fixture
def valid_trading_message():
    """Create a valid trading message."""
    return {
        "stock": "000001.SH",
        "action": "buy",
        "price": 19.60,
        "number": 1000,
    }


@pytest.fixture
def invalid_trading_message():
    """Create an invalid trading message (invalid stock code)."""
    return {
        "stock": "invalid",
        "action": "buy",
        "price": 19.60,
        "number": 1000,
    }


@pytest.fixture
def execution_success_message():
    """Create a successful execution result."""
    return {
        "status": "success",
        "order_id": "123456",
        "data": {
            "stock": "000001.SH",
            "action": "buy",
            "price": 19.60,
            "number": 1000,
        },
    }


@pytest.fixture
def execution_error_message():
    """Create an error execution result."""
    return {
        "status": "error",
        "order_id": None,
        "message": "Insufficient funds",
    }


@pytest.fixture
async def mock_token_response():
    """Create a mock token response."""
    return {"token": "test-token-123"}


@pytest.fixture
def token_response_future(mock_token_response):
    """Create an async future that returns token response."""
    future = asyncio.Future()
    future.set_result(mock_token_response)
    return future
