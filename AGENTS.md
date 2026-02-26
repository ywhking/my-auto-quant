# AGENTS.md - Agent Guidelines

## Project Overview

This is a greenfield auto-quant trading system with three Python modules:
- **trader_initiator** - Generates trading instructions, connects via WebSocket
- **qmt_proxy** - Forwards instructions, maintains persistent connections
- **trader_executor** - Executes QMT orders, handles connection monitoring

**Architecture Details:** See `系统架构.md` for the full system specification in Chinese.

---

## Build Commands

**Status:** No build system configured yet.

Recommended tools to add:
```bash
# Install dependencies (when requirements.txt is added)
pip install -r requirements.txt

# Install package in development mode (when setup.py is added)
pip install -e .
```

---

## Lint Commands

**Status:** No linting tools configured yet.

Recommended tools to add:
```bash
# Ruff (modern, fast Python linter/formatter)
pip install ruff

# Run linting
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

---

## Test Commands

**Status:** No test framework configured yet.

Recommended tools to add:
```bash
# pytest
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run single test
pytest tests/test_module.py::test_function

# Run tests with coverage
pytest --cov=. --cov-report=html
```

---

## Code Style Guidelines

### Python Version
Use Python 3.10+ for type hint features (`|` union operator) and async patterns.

### Type Hints
**Always use type hints for:**
- Function parameters and return values
- Class attributes
- Complex data structures

```python
from typing import Optional, Dict, List, Union

async def send_order(
    stock: str,
    action: Literal["buy", "sell"],
    price: float,
    number: int
) -> Dict[str, Union[str, float]]:
    ...
```

### Async/Await
This is a WebSocket-based system - use async/await for all I/O operations:
```python
import asyncio
import websockets

async def handle_connection(websocket: websockets.WebSocketServerProtocol):
    async for message in websocket:
        await process_message(message)
```

### Import Style
Follow PEP 8 - group imports in this order:
1. Standard library
2. Third-party
3. Local application

```python
import asyncio
from typing import Optional

import websockets
from pydantic import BaseModel

from trader_initiator.models import OrderRequest
```

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `WebSocketClient`, `OrderHandler`)
- **Functions/Methods:** `snake_case` (e.g., `send_order`, `handle_message`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `WS_PORT`)
- **Private:** `_single_underscore` (e.g., `_reconnect()`)

### Error Handling
Use structured error handling with logging:
```python
import logging

logger = logging.getLogger(__name__)

try:
    await websocket.send(data)
except ConnectionError as e:
    logger.error(f"WebSocket connection failed: {e}")
    raise OrderFailedError("Connection to QMT failed") from e
```

### Docstrings
Use Google-style docstrings:
```python
def execute_order(order: OrderRequest) -> OrderResult:
    """Execute a trading order via QMT client.

    Args:
        order: The order request containing stock, action, price, and quantity.

    Returns:
        OrderResult: The execution result with status and actual trade details.

    Raises:
        ConnectionError: If QMT client connection fails.
        OrderRejectedError: If the order is rejected by QMT.
    """
    ...
```

---

## Project Structure Notes

All three module directories are currently empty. When adding code:
- Create `__init__.py` files to make modules importable
- Separate concerns: models, services, handlers in each module
- Use async patterns for WebSocket communication
- Implement connection monitoring and auto-reconnection (especially in qmt_proxy and trader_executor)

---

## Key Dependencies to Consider

- `websockets` - WebSocket communication
- `pydantic` - Data validation (recommended for order structures)
- `asyncio` - Async I/O (built-in)
- `logging` - Logging (built-in, configure appropriately for production)
