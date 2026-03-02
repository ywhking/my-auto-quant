# Trader Initiator

WebSocket client that sends trading orders to QMT Proxy.

## Installation

```bash
pip install -e .
```

## Usage

### As a module

```bash
python -m trader_initiator --stock 000001.SH --action buy --price 10.5 --number 1000
```

### As a library

```python
import asyncio
from trader_initiator import send_order

async def main():
    result = await send_order(
        stock="000001.SH",
        action="buy",
        price=10.5,
        number=1000
    )
    print(result)

asyncio.run(main())
```

## Configuration

Edit `config/config.json` to set proxy URL and authentication credentials.
