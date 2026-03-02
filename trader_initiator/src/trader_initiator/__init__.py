"""Trader Initiator - Sends trading orders to QMT Proxy via WebSocket.

The trader_initiator module is responsible for:
- Generating trading instructions
- Authenticating with the QMT Proxy
- Sending orders via WebSocket connections
- Receiving and returning execution results

Usage as module:
    python -m trader_initiator --stock 000001.SH --action buy --price 10.5 --number 1000

Main Functions:
    send_order: Async function to send a trading order

Exceptions:
    ValidationError: Raised when input parameters are invalid
    OrderFailedError: Raised when order execution fails at executor level
"""

from trader_initiator.__main__ import main
from trader_initiator.client import send_order
from trader_initiator.config import Config
from trader_initiator.exceptions import OrderFailedError, ValidationError

__all__ = [
    "send_order",
    "Config",
    "ValidationError",
    "OrderFailedError",
    "main",
]

__version__ = "0.1.0"
