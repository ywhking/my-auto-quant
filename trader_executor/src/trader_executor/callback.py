"""QMT trading callback handler.

This module provides a callback class that inherits from XtQuantTraderCallback
to receive real-time order updates and trade confirmations from QMT.
"""

import logging
import threading
from typing import Any

# Try to import xtquant, but make it optional for testing
try:
    from xtquant.xttrader import XtQuantTraderCallback

    XTQUANT_AVAILABLE = True
except ImportError:
    XTQUANT_AVAILABLE = False
    # Create a dummy class for type checking when xtquant is not installed
    XtQuantTraderCallback = object  # type: ignore

from trader_executor.models import OrderCallbackResult

logger = logging.getLogger(__name__)


class ExecutorCallback(XtQuantTraderCallback):  # type: ignore
    """Callback handler for QMT order and trade events.

    This class receives real-time callbacks from QMT when:
    - Order status changes (on_order_stock)
    - Trade occurs (on_trade_stock)
    - Order error occurs (on_order_error)
    - Connection disconnects (on_disconnected)

    Results are stored in memory and can be retrieved by order ID.
    Thread-safe operations using locks.
    """

    def __init__(self) -> None:
        """Initialize the callback handler.

        Creates in-memory storage for order results and a lock for
        thread-safe operations.
        """
        self._order_results: dict[str | int, OrderCallbackResult] = {}
        self._lock = threading.Lock()

    def on_disconnected(self) -> None:
        """Handle QMT disconnection event.

        This method is called when the connection to QMT is lost.
        Logs the event for monitoring and debugging.
        """
        logger.warning("QMT connection disconnected")

    def on_order_stock(self, order: Any) -> None:
        """Handle order status update callback.

        Called when order status changes. Order status codes:
        - 50: 已报
        - 51: 待撤
        - 52: 部成
        - 53: 全成
        - 54: 已撤
        - 55: 部撤
        - 56: 废单

        Args:
            order: Order object from QMT with attributes including
                   order_id, order_status, status_msg
        """
        try:
            order_id = getattr(order, "order_id", None)
            order_status = getattr(order, "order_status", None)
            status_msg = getattr(order, "status_msg", "")

            if order_id is None:
                logger.error("Order callback received without order_id")
                return

            result = OrderCallbackResult(
                order_id=order_id,
                order_status=order_status,
                status_msg=status_msg,
            )

            with self._lock:
                self._order_results[order_id] = result

            logger.debug(
                f"Order callback: order_id={order_id}, "
                f"status={order_status}, msg={status_msg}"
            )

            if order_status == 53:
                logger.info(f"Order fully executed: order_id={order_id}")
            elif order_status == 56:
                logger.error(f"Order rejected: order_id={order_id}, msg={status_msg}")

        except Exception as e:
            logger.error(f"Error in on_order_stock callback: {e}")

    def on_trade_stock(self, trade: Any) -> None:
        """Handle trade execution callback.

        Called when a trade actually occurs (real execution).

        Args:
            trade: Trade object from QMT with attributes including
                   order_id, traded_volume, traded_price
        """
        try:
            order_id = getattr(trade, "order_id", None)
            traded_volume = getattr(trade, "traded_volume", None)
            traded_price = getattr(trade, "traded_price", None)

            if order_id is None:
                logger.error("Trade callback received without order_id")
                return

            result = OrderCallbackResult(
                order_id=order_id,
                traded_volume=traded_volume,
                traded_price=traded_price,
            )

            with self._lock:
                # Update existing result or create new one
                if order_id in self._order_results:
                    existing = self._order_results[order_id]
                    result.order_status = existing.order_status
                    result.status_msg = existing.status_msg
                self._order_results[order_id] = result

            logger.info(
                f"Trade callback: order_id={order_id}, "
                f"volume={traded_volume}, price={traded_price}"
            )

        except Exception as e:
            logger.error(f"Error in on_trade_stock callback: {e}")

    def on_order_error(self, order_error: Any) -> None:
        """Handle order error callback.

        Called when an order request is rejected directly by QMT.

        Args:
            order_error: Error object from QMT with attributes including
                         order_id, error_msg
        """
        try:
            order_id = getattr(order_error, "order_id", None)
            error_msg = getattr(order_error, "error_msg", "")

            if order_id is None:
                logger.error("Order error callback received without order_id")
                return

            result = OrderCallbackResult(
                order_id=order_id,
                status_msg=error_msg,
            )

            with self._lock:
                self._order_results[order_id] = result

            logger.error(
                f"Order error callback: order_id={order_id}, error={error_msg}"
            )

        except Exception as e:
            logger.error(f"Error in on_order_error callback: {e}")

    def get_result(self, order_id: str | int) -> OrderCallbackResult | None:
        """Get callback result for a specific order.

        Args:
            order_id: Order ID from QMT

        Returns:
            OrderCallbackResult if available, None otherwise
        """
        with self._lock:
            return self._order_results.get(order_id)

    def clear_result(self, order_id: str | int) -> None:
        """Clear callback result for a specific order.

        Args:
            order_id: Order ID from QMT
        """
        with self._lock:
            self._order_results.pop(order_id, None)

    def clear_all_results(self) -> None:
        """Clear all stored callback results."""
        with self._lock:
            self._order_results.clear()

    def get_all_results(self) -> dict[str | int, OrderCallbackResult]:
        """Get all stored callback results.

        Returns:
            Dictionary mapping order_id to OrderCallbackResult
        """
        with self._lock:
            return self._order_results.copy()
