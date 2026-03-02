# AGENTS.md - Agent Guidelines

## Project Overview

**Trader Executor** - WebSocket client that receives trading instructions from QMT Proxy, executes orders via QMT client (xtquant), and returns execution results.

**Architecture:** WebSocket client → QMT Proxy ↔ QMT Client (迅投QMT)

---

## Build Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Install optional QMT SDK (for production trading)
pip install xtquant
```

---

## Lint Commands

Uses **Ruff** for linting/formatting:

```bash
# Check all files
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Check specific file
ruff check client.py
```

---

## Test Commands

Uses **pytest** with asyncio support:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_client.py -v
pytest tests/test_qmt_client.py -v

# Run specific test class
pytest tests/test_client.py::TestExecutorClient -v

# Run specific test function
pytest tests/test_client.py::TestExecutorClient::test_process_message -v

# Run by keyword
pytest -k "test_connect" -v

# Run with coverage
pytest --cov=. --cov-report=html
```

---

## Code Style Guidelines

### Python Version
Python 3.10+. Use modern syntax:
- Union types: `str | None` (not `Optional[str]`)
- Type hints: `dict`, `list` (not `Dict`, `List`)

### Type Hints
Always annotate functions and use Pydantic for models:

```python
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class TradingMessage(BaseModel):
    """Trading message model."""
    stock: str = Field(..., description="Stock code")
    action: Literal["buy", "sell"] = Field(..., description="Action")
    price: float = Field(..., gt=0)

    @field_validator("stock")
    @classmethod
    def validate_stock_code(cls, v: str) -> str:
        pattern = r"^[0-9]{6}\.[A-Z]{2}$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid stock code: {v}")
        return v

async def place_order(stock: str, price: float) -> str:
    """Execute order and return order_id."""
    ...
```

### Async/Await
All I/O operations must be async. Use `asyncio.to_thread()` for blocking QMT calls:

```python
import asyncio
import websockets

async def connect(self) -> None:
    """Connect to QMT (blocking call in thread)."""
    await asyncio.to_thread(self._xt_trader.connect)

async def handle_messages(self, websocket: websockets.WebSocketClientProtocol) -> None:
    async for message in websocket:
        await self.process_message(message)
```

### Imports
Follow PEP 8 order (no blank lines between groups):
1. Standard library
2. Third-party
3. Local application

```python
import asyncio
import json
import logging
from typing import Any

import aiohttp
import websockets
from pydantic import BaseModel, Field

from trader_executor.config import ExecutorConfig
from trader_executor.exceptions import QMTError
```

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `ExecutorClient`, `QMTClientWrapper`)
- **Functions/Methods:** `snake_case` (e.g., `place_order`, `validate_stock`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_RECONNECT_DELAY`)
- **Private:** `_single_underscore` prefix (e.g., `_xt_trader`, `_connect()`)
- **Modules:** `snake_case` (e.g., `client.py`, `qmt_client.py`)

### Error Handling
Use custom exceptions with logging and exception chaining:

```python
import logging

logger = logging.getLogger(__name__)

try:
    await self.websocket.send(data)
except ConnectionError as e:
    logger.error(f"WebSocket failed: {e}")
    raise QMTConnectionError("Connection failed") from e
```

### Docstrings
Use Google-style docstrings:

```python
def place_order(self, stock: str, action: str, price: float, number: int) -> str:
    """Execute a trading order via QMT client.

    Args:
        stock: Stock code with exchange suffix (e.g., '000001.SH')
        action: Trading action - 'buy' or 'sell'
        price: Limit order price (must be > 0)
        number: Order quantity (must be > 0)

    Returns:
        str: Local order ID from QMT client

    Raises:
        QMTConnectionError: If QMT connection fails.
        QMTExecutionError: If order is rejected by QMT.
    """
    ...
```

---

## Testing Guidelines

- Use `pytest-asyncio` for async tests (decorate with `@pytest.mark.asyncio`)
- Mock external dependencies (QMT, WebSocket) using `unittest.mock`
- Test files: `test_*.py` in `tests/` directory
- Fixtures centralized in `tests/conftest.py`
- Use `AsyncMock` for async WebSocket methods
- Use `MagicMock` for QMT objects (order, trade, error)
- Use `patch()` for mocking module-level dependencies

---

## Key Dependencies

- `websockets` - WebSocket client for proxy connection
- `aiohttp` - Async HTTP client for token authentication
- `pydantic` - Data validation and settings
- `pytest` / `pytest-asyncio` - Testing framework
- `ruff` - Linting and formatting
- `xtquant` - QMT trading SDK (optional, production only)

---

## Project Structure

```
trader_executor/
├── __init__.py          # Package exports (ExecutorClient, exceptions, models)
├── __main__.py          # Entry point (python -m trader_executor)
├── client.py            # Main WebSocket client with auto-reconnect
├── qmt_client.py        # QMT client wrapper (XtQuantTrader async wrapper)
├── callback.py          # QMT callback handler for order/trade events
├── config.py            # Configuration management (singleton)
├── models.py            # Pydantic models (TradingMessage, ExecutionResult)
├── exceptions.py        # Custom exceptions (QMTError hierarchy)
├── risk_checker.py      # Pre-trade risk validation
├── idempotency.py       # Duplicate order prevention
├── requirements.txt     # Dependencies
├── config.json          # Runtime configuration
└── tests/               # Test files
    ├── conftest.py      # Shared fixtures
    ├── test_client.py   # WebSocket client tests
    ├── test_qmt_client.py
    ├── test_callback.py
    ├── test_models.py
    ├── test_exceptions.py
    ├── test_risk_checker.py
    └── test_idempotency.py
```

---

## Key Features

### Risk Management (`risk_checker.py`)
Pre-trade risk checks:
- Position limit: Max 50% of total assets in single stock
- Order amount limit: Max 50,000 RMB per order
- Order size: Min 100 shares, max 100,000 shares, multiple of 100
- Price limit detection: Warns on limit up/down (>9.8%)
- Trading hours: Market hours only (09:30-11:30, 13:00-15:00)

### Idempotency Handler (`idempotency.py`)
Prevents duplicate order execution:
- Caches results by `order_id`
- TTL-based expiration (default 24 hours)
- Thread-safe with asyncio locks

### Auto-Reconnection
Exponential backoff reconnection strategy:
- Initial delay: 1s, doubles each retry (max 60s)
- Max attempts: 10 (configurable)
- Applies to WebSocket connection loss

---

## Additional Notes

### Module Entry Point
- **trader_executor**: `python -m trader_executor` (uses `__main__.py`)
- Or import directly: `from trader_executor import ExecutorClient`

### Configuration File
- `config.json` - Executor configuration (proxy, auth, QMT, trading rules)

### Stock Code Format
All stock codes must follow pattern: `[0-9]{6}\.[A-Z]{2}`
- Examples: `000001.SH`, `600000.SH`, `300001.SZ`

### Trading Hours
Market hours enforced: 09:30-11:30, 13:00-15:00 (China timezone)

### Testing Notes
- All tests use mocking (no QMT installation required)
- Set `allow_mock: true` in config to enable mock mode
- Real filled price/quantity comes from callbacks, not response
