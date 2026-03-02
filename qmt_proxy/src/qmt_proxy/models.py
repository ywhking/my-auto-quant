"""Pydantic models for QMT Proxy data validation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class User(BaseModel):
    """User credential model."""

    name: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    role: str = Field(..., description="User role (initiator or executor)")
    """User credential model."""

    name: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserConfig(BaseModel):
    """User configuration model loaded from config/users.json."""

    users: list[User] = Field(..., description="List of users")


class TokenResponse(BaseModel):
    """Token response model."""

    token: str = Field(..., description="Authentication token")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")


class TradingMessage(BaseModel):
    """Trading message model (initiator -> proxy -> executor)."""

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
        import re

        pattern = r"^[0-9]{6}\.[A-Z]{2}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid stock code: {v} (expected format: XXXXXX.XX)")
        return v


class ExecutionResult(BaseModel):
    """Execution result model (executor -> proxy -> initiator)."""

    status: Literal["success", "error"] = Field(..., description="Execution status")
    data: dict | None = Field(None, description="Execution data")
    message: str | None = Field(None, description="Error message (if status is error)")


class ExecutorNotConnectedResponse(BaseModel):
    """Response when executor is not connected."""

    status: Literal["error"] = Field(default="error", description="Error status")
    message: Literal["Executor not connected"] = Field(
        default="Executor not connected",
        description="Error message",
    )
