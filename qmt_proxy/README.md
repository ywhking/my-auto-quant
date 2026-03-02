# QMT Proxy

Trading message relay between Trading Initiator and Trading Executor.

## Features

- **REST API**: Token-based authentication (`GET /auth`)
- **WebSocket Endpoint**: Real-time message forwarding (`GET /ws?token=<token>`)
- **Role-based Connections**: Supports "initiator" (northbound) and "executor" (southbound)
- **Message Routing**: Forwards messages between initiator and executor
- **Error Handling**: Rejects messages when executor is not connected
- **Health Monitoring**: Health check endpoint for connection status

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create `config/users.json` in the qmt_proxy directory:

```json

Create `config/users.json` in the parent directory (or update existing):

```json
{
  "users": [
    {
      "name": "initiator",
      "password": "xxxxxxx"
    },
    {
      "name": "executor",
      "password": "xxxxxxx"
    }
  ]
}
```

## Running

Start the proxy server:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Or run directly:

```bash
python main.py
```

## API Endpoints

### Authentication

`GET /auth?userName=<username>&password=<password>`

Returns a token for WebSocket connection:

```json
{
  "token": "abc123-def456-ghi789"
}
```

### WebSocket

`GET /ws?token=<token>`

Establishes WebSocket connection. Connection role is determined by authenticated user.

### Health Check

`GET /health`

Returns connection status:

```json
{
  "status": "healthy",
  "connections": ["initiator", "executor"],
  "count": 2
}
```

### Test Reset (Testing Only)

`POST /test/reset`

Clears all tokens and connections.

## Message Formats

### Trading Message (Initiator → Proxy → Executor)

```json
{
  "stock": "000001.SH",
  "action": "buy|sell",
  "price": 20.00,
  "number": 1000
}
```

### Execution Result (Executor → Proxy → Initiator)

```json
{
  "status": "success|error",
  "data": {
    "stock": "000001.SH",
    "action": "buy|sell",
    "price": 19.60,
    "number": 1000
  },
  "message": "Error message (if status is error)"
}
```

## Testing

Run tests from project root:

```bash
cd qmt_proxy
python -m pytest ../tests/ -v
```

## Project Structure

```
qmt_proxy/
├── __init__.py           # Module initialization
├── auth.py              # Token management and validation
├── connection_manager.py  # WebSocket connection management
├── exceptions.py         # Custom exceptions
├── main.py              # FastAPI application
├── models.py            # Pydantic data models
├── requirements.txt      # Project dependencies
├── config/               # Configuration directory
│   └── users.json      # User credentials
└── README.md            # This file

../config/
└── users.json            # User credentials
└── users.json            # User credentials

../tests/
├── conftest.py         # Test configuration
├── test_auth.py         # Authentication tests
├── test_connection_manager.py  # Connection manager tests
├── test_models.py       # Model tests
└── test_websocket.py     # WebSocket endpoint tests
```

## Error Handling

When executor is not connected, the proxy returns:

```json
{
  "status": "error",
  "message": "Executor not connected"
}
```

## Dependencies

- fastapi>=0.104.0 - REST API framework
- uvicorn[standard]>=0.24.0 - ASGI server
- pydantic>=2.0.0 - Data validation
- pytest>=7.4.0 - Testing framework
- pytest-asyncio>=0.21.0 - Async test support
