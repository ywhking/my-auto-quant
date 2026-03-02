"""Main client module for trader_initiator.

This module contains the core send_order function and helper functions
for communicating with the QMT Proxy via WebSocket.
"""

import asyncio
import json
import logging
import re
import uuid

import ssl
import aiohttp
import websockets


from trader_initiator.config import Config
from trader_initiator.exceptions import OrderFailedError, ValidationError

logger = logging.getLogger(__name__)

# Configuration singleton
_config = Config()


def _get_ssl_context(config: Config) -> ssl.SSLContext | None:
    """Get SSL context based on configuration.

    Args:
        config: Configuration object

    Returns:
        SSL context for aiohttp/websockets connections, or None if HTTP mode.
    """
    if not config.use_https:
        # HTTP mode - no SSL needed
        return None

    if config.verify_ssl:
        # HTTPS with certificate verification
        return ssl.create_default_context()
    else:
        # HTTPS without certificate verification (for self-signed certs)
        return ssl._create_unverified_context()


def validate_stock_code(stock: str) -> bool:
    r"""Validate stock code format.

    Stock code must match pattern: [0-9]{6}\.(SH|SZ)
    Examples: 600000.SH (Shanghai), 000001.SZ (Shenzhen)

    Args:
        stock: Stock code string to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[0-9]{6}\.(SH|SZ)$"
    return bool(re.match(pattern, stock))


def validate_order_params(stock: str, action: str, price: float, number: int) -> None:
    """Validate all order parameters.

    Args:
        stock: Stock code (e.g., "000001.SH")
        action: Trading action ("buy" or "sell")
        price: Order price (must be > 0)
        number: Order quantity (must be > 0)

    Raises:
        ValidationError: If any parameter is invalid
    """
    if not validate_stock_code(stock):
        msg = f"Invalid stock code: {stock} (expected format: XXXXXX.XX)"
        logger.error(msg)
        raise ValidationError(msg)

    if action not in ("buy", "sell"):
        msg = f"Invalid action: {action} (expected 'buy' or 'sell')"
        logger.error(msg)
        raise ValidationError(msg)

    if price <= 0:
        msg = f"Price must be positive: {price}"
        logger.error(msg)
        raise ValidationError(msg)

    if number <= 0:
        msg = f"Number must be positive: {number}"
        logger.error(msg)
        raise ValidationError(msg)


async def get_token(config: Config | None = None) -> str:
    """Get authentication token from QMT Proxy.

    Makes a GET request to the proxy's token endpoint to obtain
    an authentication token for WebSocket connections.

    Args:
        config: Configuration object (uses default if None)

    Returns:
        Authentication token string

    Raises:
        ConnectionError: If the request fails or returns non-200 status
    """
    cfg = config or _config
    ssl_context = _get_ssl_context(cfg)
    url = f"{cfg.token_url}?userName={cfg.username}&password={cfg.password}"

    logger.debug(f"Requesting token from: {cfg.proxy_url}")

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    token = data["token"]
                    logger.debug("Token obtained successfully")
                    return token
                error_msg = f"Authentication failed: HTTP {response.status}"
                logger.error(error_msg)
                raise ConnectionError(error_msg)
    except (aiohttp.ClientError, json.JSONDecodeError) as e:
        error_msg = f"Failed to get token: {e}"
        logger.error(error_msg)
        raise ConnectionError(error_msg) from e
    except Exception as e:
        # Catch any other unexpected exception
        if isinstance(e, ConnectionError):
            # Re-raise if it's already a ConnectionError
            raise
        error_msg = f"Failed to get token: {e}"
        logger.error(error_msg)
        raise ConnectionError(error_msg) from e


async def check_executor_online(config: Config | None = None) -> bool:
    """Check if Executor is connected to Proxy.

    Queries the Proxy's /health endpoint to verify that
    the Executor role is currently connected.

    Args:
        config: Configuration object (uses default if None)

    Returns:
        True if Executor is online, False otherwise
    """
    cfg = config or _config
    ssl_context = _get_ssl_context(cfg)
    health_url = f"{cfg.proxy_url}/health"
    health_url = f"{cfg.proxy_url}/health"

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context) if ssl_context else None
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                health_url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    connections = data.get("connections", [])
                    is_online = "executor" in connections
                    logger.debug(
                        f"Executor online status: {is_online} (connections={connections})"
                    )
                    return is_online
                logger.warning(f"Health check failed: HTTP {response.status}")
                return False
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(f"Health check failed: {e}")
        return False


def generate_order_id() -> str:
    """Generate a unique order ID in UUID format.

    Returns:
        UUID string (e.g., "550e8400-e29b-41d4-a716-446655440000")
    """
    return str(uuid.uuid4())


async def send_order(
    stock: str, action: str, price: float, number: int, config: Config | None = None
) -> dict:
    """Execute a trading order asynchronously.

    This is the main entry point for submitting trading orders. It:
    1. Validates the input parameters
    2. Checks if Executor is online
    3. Generates a unique order ID
    4. Obtains authentication token from proxy
    5. Establishes WebSocket connection
    6. Sends the order message
    7. Waits for execution result with timeout
    8. Returns the result or raises appropriate exception

    Args:
        stock: Stock code with exchange suffix (e.g., "000001.SH")
        action: Trading action - "buy" or "sell"
        price: Limit order price (must be > 0)
        number: Order quantity (must be > 0)
        config: Optional configuration object (uses default if None)

    Returns:
        Execution result dictionary with status and data.
        Example: {"status": "success", "order_id": "uuid", "data": {...}}

    Raises:
        ValidationError: If input parameters are invalid
        ConnectionError: If cannot connect to proxy or Executor is offline
        TimeoutError: If order execution times out
        OrderFailedError: If proxy returns error response
    """
    cfg = config or _config
    ssl_context = _get_ssl_context(cfg)

    # 1. Validate parameters
    validate_order_params(stock, action, price, number)

    # 3. Generate order ID
    order_id = generate_order_id()
    logger.info(
        f"Order requested: order_id={order_id}, stock={stock}, "
        f"action={action}, price={price}, number={number}"
    )

    # 4. Get authentication token
    token = await get_token(cfg)

    # 5. Connect to WebSocket (one-time connection per order)
    ws_url = f"{cfg.ws_url}{cfg.ws_path}?token={token}"

    try:
        async with websockets.connect(
            ws_url, close_timeout=cfg.timeout, ping_interval=None, ssl=ssl_context
        ) as websocket:
            logger.debug(f"WebSocket connected: {ws_url}")
            logger.debug(f"WebSocket connected: {ws_url}")

            # 6. Send trading message
            order_message = {
                "order_id": order_id,
                "stock": stock,
                "action": action,
                "price": price,
                "number": number,
            }
            await websocket.send(json.dumps(order_message))
            logger.info(
                f"Order sent: order_id={order_id}, stock={stock}, action={action}"
            )

            # 7. Wait for result with timeout
            try:
                response_raw = await asyncio.wait_for(
                    websocket.recv(), timeout=cfg.timeout
                )
            except asyncio.TimeoutError:
                msg = (
                    f"Order timeout: order_id={order_id}, stock={stock}, "
                    f"action={action} (timeout={cfg.timeout}s)"
                )
                logger.error(msg)
                raise TimeoutError(msg) from None

            # 8. Parse and handle result
            try:
                result = json.loads(response_raw)
            except json.JSONDecodeError as e:
                msg = (
                    f"Invalid JSON response: order_id={order_id}, "
                    f"response={response_raw[:100]}"
                )
                logger.error(msg)
                raise OrderFailedError(msg) from e

            logger.debug(
                f"Response received: order_id={order_id}, status={result.get('status')}"
            )

            # 9. Handle response
            if result.get("status") == "success":
                logger.info(
                    f"Order executed successfully: order_id={order_id}, "
                    f"data={result.get('data')}"
                )
                return result

            # Error response from proxy/executor
            error_msg = result.get("message", "Unknown error")
            msg = (
                f"Order failed: order_id={order_id}, "
                f"stock={stock}, action={action}, error={error_msg}"
            )
            logger.error(msg)
            raise OrderFailedError(msg)

    except websockets.exceptions.InvalidURI as e:
        msg = f"Invalid WebSocket URL: {ws_url}"
        logger.error(f"{msg}: {e}")
        raise ConnectionError(msg) from e
    except websockets.exceptions.WebSocketException as e:
        msg = (
            f"WebSocket connection failed: order_id={order_id}, "
            f"stock={stock}, action={action}"
        )
        logger.error(f"{msg}: {e}")
        raise ConnectionError(msg) from e
    except TimeoutError:
        # Re-raise TimeoutError without wrapping
        raise
    except OSError as e:
        msg = f"Connection error: order_id={order_id}, stock={stock}, action={action}"
        logger.error(f"{msg}: {e}")
        raise ConnectionError(msg) from e
    except Exception as e:
        # Catch any other unexpected exception during connection
        if isinstance(e, (ConnectionError, TimeoutError, OrderFailedError)):
            # Re-raise if it's already one of our expected exceptions
            raise
        msg = f"Connection error: order_id={order_id}, stock={stock}, action={action}"
        logger.error(f"{msg}: {e}")
        raise ConnectionError(msg) from e
