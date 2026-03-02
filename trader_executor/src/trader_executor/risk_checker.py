"""Risk management checker for trader_executor.

Provides pre-trade risk checks including:
- Position limits
- Order amount limits
- Price validation (limit up/down)
- Trading hours validation
- Order size validation
"""

import logging
from datetime import datetime
from typing import Literal

from .config import ExecutorConfig

logger = logging.getLogger(__name__)


class RiskCheckError(Exception):
    """Raised when a risk check fails."""

    pass


class RiskChecker:
    """Pre-trade risk checker.

    Validates trading orders before execution to prevent:
    - Over-concentration in single stock
    - Excessive order amounts
    - Trading outside market hours
    - Invalid order sizes
    - Price anomalies (limit up/down)
    """

    def __init__(self, config: ExecutorConfig | None = None) -> None:
        """Initialize RiskChecker.

        Args:
            config: Optional configuration object
        """
        self.config = config or ExecutorConfig()
        self.risk_config = self._get_risk_config()

    def _get_risk_config(self) -> dict:
        """Get risk management configuration.

        Returns:
            Risk configuration dictionary
        """
        return {
            "max_position_ratio": 0.5,  # 单票最大仓位 50%
            "max_order_amount": 50000,  # 单笔最大金额 5 万
            "min_order_number": 100,  # 最小下单 100 股
            "max_order_number": 100000,  # 单笔最大 10 万股
            "price_warn_ratio": 0.098,  # 涨跌停预警 9.8%
            "trading_hours": {
                "morning": ("00:00:00", "23:59:59"),
                "afternoon": ("00:00:00", "00:00:00"),
            },
        }

    def check_all(
        self,
        stock: str,
        action: Literal["buy", "sell"],
        price: float,
        number: int,
        current_position: int = 0,
        total_assets: float = 0.0,
        prev_close: float = 0.0,
    ) -> tuple[bool, str | None]:
        """Run all risk checks.

        Args:
            stock: Stock code (e.g., '000001.SH')
            action: Trading action ('buy' or 'sell')
            price: Order price
            number: Order quantity
            current_position: Current holding quantity (default 0)
            total_assets: Total account assets (default 0)
            prev_close: Previous close price for limit check (default 0)

        Returns:
            Tuple of (passed: bool, error_message: str | None)
        """
        checks = [
            ("trading_hours", self.check_trading_hours),
            ("order_size", lambda: self.check_order_size(number)),
            ("order_amount", lambda: self.check_order_amount(price, number)),
            (
                "position_limit",
                lambda: self.check_position_limit(
                    stock, action, price, number, current_position, total_assets
                ),
            ),
            (
                "price_limit",
                lambda: self.check_price_limit(stock, price, prev_close),
            ),
        ]

        for check_name, check_func in checks:
            try:
                if not check_func():
                    return False, f"Risk check failed: {check_name}"
            except RiskCheckError as e:
                logger.warning(f"Risk check {check_name} failed: {e}")
                return False, str(e)

        logger.info(f"All risk checks passed for {stock} {action}")
        return True, None

    def check_trading_hours(self) -> bool:
        """Check if current time is within trading hours.

        Returns:
            True if within trading hours, False otherwise

        Raises:
            RiskCheckError: If outside trading hours
        """
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")

        trading_hours = self.risk_config["trading_hours"]
        morning_start, morning_end = trading_hours["morning"]
        afternoon_start, afternoon_end = trading_hours["afternoon"]

        is_morning = morning_start <= current_time <= morning_end
        is_afternoon = afternoon_start <= current_time <= afternoon_end

        if not (is_morning or is_afternoon):
            raise RiskCheckError(
                f"Outside trading hours: current={current_time}, "
                f"morning={morning_start}-{morning_end}, "
                f"afternoon={afternoon_start}-{afternoon_end}"
            )

        return True

    def check_order_size(self, number: int) -> bool:
        """Check if order size is within limits.

        Args:
            number: Order quantity

        Returns:
            True if valid, False otherwise

        Raises:
            RiskCheckError: If order size is invalid
        """
        min_num = self.risk_config["min_order_number"]
        max_num = self.risk_config["max_order_number"]

        if number < min_num:
            raise RiskCheckError(
                f"Order size too small: {number} < {min_num}"
            )

        if number > max_num:
            raise RiskCheckError(
                f"Order size too large: {number} > {max_num}"
            )

        # Check lot size (A 股通常 100 股一手)
        lot_size = self.config.lot_size
        if number % lot_size != 0:
            raise RiskCheckError(
                f"Order size must be multiple of {lot_size}: {number}"
            )

        return True

    def check_order_amount(self, price: float, number: int) -> bool:
        """Check if order amount is within limits.

        Args:
            price: Order price
            number: Order quantity

        Returns:
            True if valid, False otherwise

        Raises:
            RiskCheckError: If order amount exceeds limit
        """
        amount = price * number
        max_amount = self.risk_config["max_order_amount"]

        if amount > max_amount:
            raise RiskCheckError(
                f"Order amount exceeds limit: {amount:.2f} > {max_amount}"
            )

        logger.debug(f"Order amount check passed: {amount:.2f} <= {max_amount}")
        return True

    def check_position_limit(
        self,
        stock: str,
        action: Literal["buy", "sell"],
        price: float,
        number: int,
        current_position: int,
        total_assets: float,
    ) -> bool:
        """Check position concentration limit.

        Args:
            stock: Stock code
            action: Trading action
            price: Order price
            number: Order quantity
            current_position: Current holding quantity
            total_assets: Total account assets

        Returns:
            True if valid, False otherwise

        Raises:
            RiskCheckError: If position limit exceeded
        """
        # Only check for buy orders
        if action != "buy":
            return True

        if total_assets <= 0:
            logger.warning("Total assets is 0, skipping position check")
            return True

        max_ratio = self.risk_config["max_position_ratio"]
        new_position_value = (current_position + number) * price
        new_ratio = new_position_value / total_assets

        if new_ratio > max_ratio:
            raise RiskCheckError(
                f"Position limit exceeded: {new_ratio:.2%} > {max_ratio:.2%} "
                f"(stock={stock}, current={current_position}, add={number})"
            )

        logger.debug(
            f"Position check passed: {new_ratio:.2%} <= {max_ratio:.2%}"
        )
        return True

    def check_price_limit(
        self, stock: str, price: float, prev_close: float
    ) -> bool:
        """Check if price is within limit up/down range.

        Args:
            stock: Stock code
            price: Order price
            prev_close: Previous close price

        Returns:
            True if valid, False otherwise

        Raises:
            RiskCheckError: If price exceeds limit
        """
        if prev_close <= 0:
            logger.warning(f"Invalid prev_close for {stock}, skipping price check")
            return True

        price_ratio = abs(price - prev_close) / prev_close
        max_ratio = self.risk_config["price_warn_ratio"]

        if price_ratio > max_ratio:
            direction = "up" if price > prev_close else "down"
            raise RiskCheckError(
                f"Price limit {direction} detected: {price_ratio:.2%} > {max_ratio:.2%} "
                f"(stock={stock}, price={price}, prev_close={prev_close})"
            )

        logger.debug(
            f"Price check passed: {price_ratio:.2%} <= {max_ratio:.2%}"
        )
        return True
