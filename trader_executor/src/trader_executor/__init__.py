"""Trader Executor module.

This module provides the ExecutorClient that connects to QMT Proxy,
executes trading orders via QMT, and returns execution results.

Key components:
- ExecutorClient: Main WebSocket client
- QMTClientWrapper: QMT client with async support
- RiskChecker: Pre-trade risk management
- IdempotencyHandler: Duplicate order prevention

Usage as module:
    python -m trader_executor
    python -m trader_executor --config /path/to/config.json
"""

# from trader_executor.client import ExecutorClient
from trader_executor.config import ExecutorConfig
from trader_executor.exceptions import QMTConnectionError, QMTExecutionError
from trader_executor.idempotency import IdempotencyHandler
from trader_executor.main import main
from trader_executor.models import ExecutionResult, TradingMessage
from trader_executor.qmt_client import QMTClientWrapper
from trader_executor.risk_checker import RiskChecker, RiskCheckError

__all__ = [
    "ExecutorClient",
    "ExecutorConfig",
    "QMTClientWrapper",
    "RiskChecker",
    "RiskCheckError",
    "IdempotencyHandler",
    "ExecutionResult",
    "TradingMessage",
    "QMTConnectionError",
    "QMTExecutionError",
    "main",
]
