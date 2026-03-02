"""QMT client wrapper.

This module provides a wrapper around xtquant.XtQuantTrader that handles
blocking calls with asyncio.to_thread() or ThreadPoolExecutor.
"""

import asyncio
import logging
import random
from typing import Optional

from xtquant import xtconstant
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

from trader_executor.callback import ExecutorCallback
from trader_executor.config import ExecutorConfig
from trader_executor.exceptions import QMTConnectionError, QMTExecutionError

logger = logging.getLogger(__name__)


class QMTClientWrapper:
    """Wrapper for QMT client with async support.

    This class wraps xtquant.XtQuantTrader to provide:
    - Async-compatible interface using asyncio.to_thread()
    - Connection management with error handling
    - Order placement with proper parameter conversion
    - Callback registration for order updates
    """

    def __init__(self, config: ExecutorConfig) -> None:
        """Initialize QMT client wrapper.

        Args:
            config: Optional configuration object (uses default if None)
        """
        self.qmt_min_path = config.qmt_min_path
        self.session_id = random.randint(100000, 999999)
        self._xt_trader = XtQuantTrader(self.qmt_min_path, self.session_id)
        logger.info("XtQuantTrader initialized with min_path=%s and session_id=%d", self.qmt_min_path, self.session_id)
        self.qmt_account_id = config.qmt_account_id
        self._account = StockAccount(self.qmt_account_id)
        logger.info("StockAccount created with account_id=%s", self.qmt_account_id)
        self._callback: Optional[ExecutorCallback] = None
        self._connected = False
        self._subscribed = False

    async def connect(self) -> None:
        """Connect to QMT client.

        Initializes XtQuantTrader with min_path and session_id,
        connects to QMT, and subscribes to account.

        Raises:
            QMTConnectionError: If connection or subscription fails
        """

        try:
            # Register callback
            self._callback = ExecutorCallback()
            await asyncio.to_thread(self._xt_trader.register_callback, self._callback)
            logger.info("Callback registered")

            # Start trading thread
            await asyncio.to_thread(self._xt_trader.start)
            logger.info("Trading thread started")

            # Connect to QMT
            connect_result = await asyncio.to_thread(self._xt_trader.connect)
            if connect_result != 0:
                raise QMTConnectionError(
                    f"QMT connection failed with code: {connect_result}"
                )
            self._connected = True
            logger.info("QMT connected successfully")

            # Subscribe to account
            subscribe_result = await asyncio.to_thread(
                self._xt_trader.subscribe, self._account
            )
            if subscribe_result != 0:
                raise QMTConnectionError(
                    f"QMT subscription failed with code: {subscribe_result}"
                )
            logger.info(f"QMT account subscribed successfully, account: {self.qmt_account_id}")
            self._subscribed = True

        except QMTConnectionError:
            raise
        except Exception as e:
            error_msg = f"Failed to connect to QMT: {e}"
            logger.error(error_msg)
            raise QMTConnectionError(error_msg) from e

    async def place_order(
        self, stock: str, action: str, price: float, number: int
    ) -> int:
        """Place an order via QMT client.

        Args:
            stock: Stock code (e.g., '000001.SH')
            action: Trading action - 'buy' or 'sell'
            price: Limit order price
            number: Order quantity

        Returns:
            Order ID from QMT

        Raises:
            QMTExecutionError: If order placement fails
            QMTConnectionError: If not connected to QMT
        """
        if not self._connected:
            raise QMTConnectionError("Not connected to QMT client")

        try:
            # Convert action to xtconstant
            if action == "buy":
                xt_action = xtconstant.STOCK_BUY
            elif action == "sell":
                xt_action = xtconstant.STOCK_SELL
            else:
                raise QMTExecutionError(f"Invalid action: {action}")

            # Place order
            order_id = await asyncio.to_thread(
                self._xt_trader.order_stock,
                self._account,
                stock,
                xt_action,
                number,
                xtconstant.FIX_PRICE,
                price,
            )

            if order_id <= 0:
                raise QMTExecutionError(
                    f"Order placement failed with order_id={order_id}"
                )

            logger.info(
                f"Order placed: order_id={order_id}, stock={stock}, "
                f"action={action}, price={price}, number={number}"
            )

            return order_id

        except QMTExecutionError:
            raise
        except Exception as e:
            error_msg = f"Failed to place order: {e}"
            logger.error(error_msg)
            raise QMTExecutionError(error_msg) from e

    async def disconnect(self) -> None:
        """Disconnect from QMT client."""
        if self._xt_trader and self._connected:
            try:
                await asyncio.to_thread(self._xt_trader.stop)
                logger.info("QMT client stopped")
            except Exception as e:
                logger.error(f"Error stopping QMT client: {e}")
        # Always reset connection state
        self._connected = False
        self._subscribed = False
        self._xt_trader = None
        self._account = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to QMT client.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    @property
    def is_subscribed(self) -> bool:
        """Check if subscribed to QMT account.

        Returns:
            True if subscribed, False otherwise
        """
        return self._subscribed

    @property
    def callback(self) -> Optional[ExecutorCallback]:
        """Get the callback handler.

        Returns:
            ExecutorCallback instance or None
        """
        return self._callback

    @property
    def xt_trader(self) -> Optional[any]:
        """Get the underlying XtQuantTrader instance.

        Returns:
            XtQuantTrader instance or None
        """
        return self._xt_trader
