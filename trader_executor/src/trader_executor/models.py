"""Pydantic models for trader_executor data validation."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradingMessage(BaseModel):
    """Trading message model (proxy -> executor).

    This model represents a trading instruction received from the QMT Proxy
    and validated before execution via QMT client.

    Attributes:
        stock: Stock code with exchange suffix (e.g., '000001.SH')
        action: Trading action - 'buy' or 'sell'
        price: Limit order price (must be > 0)
        number: Order quantity (must be > 0)
    """

    stock: str = Field(..., description="Stock code (e.g., '000001.SH')")
    action: Literal["buy", "sell"] = Field(..., description="Trading action")
    price: float = Field(..., gt=0, description="Limit order price")
    number: int = Field(..., gt=0, description="Order quantity")

    @field_validator("stock")
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        r"""Validate stock code format: [0-9]{6}\.[A-Z]{2}.

        Args:
            v: Stock code string to validate

        Returns:
            Validated stock code

        Raises:
            ValueError: If stock code format is invalid
        """
        pattern = r"^[0-9]{6}\.[A-Z]{2}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid stock code: {v} (expected format: XXXXXX.XX)")
        return v


class ExecutionResult(BaseModel):
    """Execution result model (executor -> proxy).

    This model represents the result of order execution returned to QMT Proxy.
    Note: Response only indicates success/failure of order submission.
    Real filled price/quantity comes from callbacks.

    Attributes:
        status: Execution status - 'success' or 'error'
        order_id: Local order ID from QMT client
        data: Execution data (stock, action, price, number)
        message: Error message (if status is 'error')
    """

    status: Literal["success", "error"] = Field(..., description="Execution status")
    order_id: str | None = Field(None, description="Order ID from QMT")
    data: dict | None = Field(None, description="Execution data")
    message: str | None = Field(None, description="Error message (if status is error)")


class ExecutorConfigModel(BaseModel):
    """Executor configuration model.

    This model represents the full configuration for the trading executor
    including proxy connection, authentication, QMT settings, connection
    management, trading rules, and logging.

    Attributes:
        proxy: Proxy server configuration
        auth: Authentication credentials
        qmt: QMT client configuration
        connection: Connection management settings
        trading: Trading parameters and rules
        logging: Logging configuration
    """

    proxy: dict = Field(..., description="Proxy server configuration")
    auth: dict = Field(..., description="Authentication credentials")
    qmt: dict = Field(..., description="QMT client configuration")
    connection: dict = Field(..., description="Connection management settings")
    trading: dict = Field(..., description="Trading parameters and rules")
    logging: dict = Field(..., description="Logging configuration")


class OrderData(BaseModel):
    """Order data included in execution result.

    This model represents the order details sent back to the proxy
    after successful order submission to QMT.

    Attributes:
        stock: Stock code
        action: Trading action
        price: Order price
        number: Order quantity
    """

    stock: str = Field(..., description="Stock code")
    action: Literal["buy", "sell"] = Field(..., description="Trading action")
    price: float = Field(..., description="Order price")
    number: int = Field(..., description="Order quantity")


class OrderCallbackResult(BaseModel):
    """Order callback result from QMT.

    This model represents the real-time callback data received from QMT
    when order status changes (on_order_stock) or trades occur (on_trade_stock).

    Attributes:
        order_id: Order ID from QMT
        order_status: Order status code
        status_msg: Order status message
        traded_volume: Traded quantity (from on_trade_stock)
        traded_price: Traded price (from on_trade_stock)
    """

    order_id: str | int = Field(..., description="Order ID from QMT")
    order_status: int | None = Field(None, description="Order status code")
    status_msg: str | None = Field(None, description="Order status message")
    traded_volume: int | None = Field(None, description="Traded quantity")
    traded_price: float | None = Field(None, description="Traded price")
