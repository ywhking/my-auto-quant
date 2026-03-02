"""Tests for trader_initiator client."""

import ssl
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest

from trader_initiator.client import (
    _get_ssl_context,
    check_executor_online,
    generate_order_id,
    get_token,
    send_order,
    validate_order_params,
    validate_stock_code,
)
from trader_initiator.exceptions import ValidationError


class TestStockCodeValidation:
    """Test stock code validation."""

    def test_valid_sh_stock(self):
        """Test valid Shanghai stock code."""
        assert validate_stock_code("600000.SH") is True
        assert validate_stock_code("000001.SH") is True

    def test_valid_sz_stock(self):
        """Test valid Shenzhen stock code."""
        assert validate_stock_code("000001.SZ") is True
        assert validate_stock_code("300001.SZ") is True

    def test_invalid_stock_code(self):
        """Test invalid stock codes."""
        assert validate_stock_code("600000") is False
        assert validate_stock_code("SH600000") is False
        assert validate_stock_code("600000.SS") is False
        assert validate_stock_code("ABC123.SH") is False


class TestOrderParamsValidation:
    """Test order parameter validation."""

    def test_valid_params(self):
        """Test valid order parameters."""
        # Should not raise
        validate_order_params("000001.SH", "buy", 10.0, 100)
        validate_order_params("600000.SH", "sell", 20.5, 500)

    def test_invalid_stock(self):
        """Test invalid stock code."""
        with pytest.raises(ValidationError, match="Invalid stock code"):
            validate_order_params("INVALID", "buy", 10.0, 100)

    def test_invalid_action(self):
        """Test invalid action."""
        with pytest.raises(ValidationError, match="Invalid action"):
            validate_order_params("000001.SH", "hold", 10.0, 100)

    def test_invalid_price(self):
        """Test invalid price."""
        with pytest.raises(ValidationError, match="Price must be positive"):
            validate_order_params("000001.SH", "buy", 0, 100)
        with pytest.raises(ValidationError, match="Price must be positive"):
            validate_order_params("000001.SH", "buy", -10.0, 100)

    def test_invalid_number(self):
        """Test invalid order quantity."""
        with pytest.raises(ValidationError, match="Number must be positive"):
            validate_order_params("000001.SH", "buy", 10.0, 0)


class TestGenerateOrderId:
    """Test order ID generation."""

    def test_generate_order_id_format(self):
        """Test that generate_order_id returns a valid UUID."""
        order_id = generate_order_id()
        assert isinstance(order_id, str)
        assert len(order_id) == 36  # Standard UUID length
        assert order_id.count("-") == 4  # UUID has 4 hyphens


class TestSSLContext:
    """Test SSL context generation for HTTPS support."""

    def test_ssl_context_http_mode(self):
        """Test SSL context returns None for HTTP mode."""
        mock_config = Mock()
        mock_config.use_https = False
        mock_config.verify_ssl = True

        result = _get_ssl_context(mock_config)
        assert result is None

    def test_ssl_context_https_with_verification(self):
        """Test SSL context with certificate verification."""
        mock_config = Mock()
        mock_config.use_https = True
        mock_config.verify_ssl = True

        result = _get_ssl_context(mock_config)
        assert isinstance(result, ssl.SSLContext)

    def test_ssl_context_https_without_verification(self):
        """Test SSL context without certificate verification (for self-signed certs)."""
        mock_config = Mock()
        mock_config.use_https = True
        mock_config.verify_ssl = False

        result = _get_ssl_context(mock_config)
        assert isinstance(result, ssl.SSLContext)
        # The unverified context should have CERT_NONE
        assert result.verify_mode == ssl.CERT_NONE


class TestConfigURLs:
    """Test URL generation based on HTTPS configuration."""

    def test_http_urls(self):
        """Test URL generation for HTTP mode."""
        mock_config = Mock()
        mock_config.use_https = False
        mock_config.proxy_host = "localhost"
        mock_config.proxy_port = 8000
        mock_config.ws_path = "/ws"
        mock_config.token_path = "/token"

        # Calculate URLs as the Config class would
        protocol = "https" if mock_config.use_https else "http"
        ws_protocol = "wss" if mock_config.use_https else "ws"

        proxy_url = f"{protocol}://{mock_config.proxy_host}:{mock_config.proxy_port}"
        token_url = f"{proxy_url}{mock_config.token_path}"
        ws_url = f"{ws_protocol}://{mock_config.proxy_host}:{mock_config.proxy_port}"

        assert proxy_url == "http://localhost:8000"
        assert token_url == "http://localhost:8000/token"
        assert ws_url == "ws://localhost:8000"

    def test_https_urls(self):
        """Test URL generation for HTTPS mode."""
        mock_config = Mock()
        mock_config.use_https = True
        mock_config.proxy_host = "localhost"
        mock_config.proxy_port = 8443
        mock_config.ws_path = "/ws"
        mock_config.token_path = "/token"

        # Calculate URLs as the Config class would
        protocol = "https" if mock_config.use_https else "http"
        ws_protocol = "wss" if mock_config.use_https else "ws"

        proxy_url = f"{protocol}://{mock_config.proxy_host}:{mock_config.proxy_port}"
        token_url = f"{proxy_url}{mock_config.token_path}"
        ws_url = f"{ws_protocol}://{mock_config.proxy_host}:{mock_config.proxy_port}"

        assert proxy_url == "https://localhost:8443"
        assert token_url == "https://localhost:8443/token"
        assert ws_url == "wss://localhost:8443"


@pytest.mark.asyncio
async def test_check_executor_online_success():
    """Test executor online check when executor is connected."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"connections": ["initiator", "executor"]}
    )
    # Make mock_response an async context manager
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await check_executor_online()
        assert result is True


@pytest.mark.asyncio
async def test_check_executor_online_offline():
    """Test executor online check when executor is disconnected."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"connections": ["initiator"]})
    # Make mock_response an async context manager
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await check_executor_online()
        assert result is False


@pytest.mark.asyncio
async def test_check_executor_online_error():
    """Test executor online check when health endpoint fails."""
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.json = AsyncMock(return_value={})
    # Make mock_response an async context manager
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("aiohttp.ClientSession", return_value=mock_session):
        result = await check_executor_online()
        assert result is False


@pytest.mark.asyncio
async def test_check_executor_online_uses_ssl_context():
    """Test that check_executor_online passes SSL context to aiohttp via connector."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"connections": ["executor"]})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = True
    mock_config.proxy_url = "https://localhost:8000"

    mock_ssl_context = ssl.create_default_context()

    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_session_cls:
        with patch("trader_initiator.client._get_ssl_context") as mock_get_ssl:
            mock_get_ssl.return_value = mock_ssl_context

            await check_executor_online(mock_config)

            # Verify SSL context was retrieved
            mock_get_ssl.assert_called_once_with(mock_config)
            # Verify ClientSession was called (with connector containing SSL)
            mock_session_cls.assert_called_once()


# ==================== HTTP Protocol Tests ====================


@pytest.mark.asyncio
async def test_get_token_http():
    """Test get_token with HTTP protocol (no SSL)."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"token": "test-token-123"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_config = Mock()
    mock_config.use_https = False
    mock_config.verify_ssl = True
    mock_config.token_url = "http://localhost:8000/token"
    mock_config.username = "testuser"
    mock_config.password = "testpass"

    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_session_cls:
        with patch("trader_initiator.client._get_ssl_context") as mock_get_ssl:
            mock_get_ssl.return_value = None

            token = await get_token(mock_config)

            assert token == "test-token-123"
            # Verify SSL context was called
            mock_get_ssl.assert_called_once_with(mock_config)
            # Verify connector was None (HTTP mode)
            call_kwargs = (
                mock_session_cls.call_args.kwargs
                if hasattr(mock_session_cls.call_args, "kwargs")
                else mock_session_cls.call_args[1]
            )
            assert call_kwargs.get("connector") is None


@pytest.mark.asyncio
async def test_send_order_http_success():
    """Test send_order complete flow with HTTP protocol."""
    mock_token_response = AsyncMock()
    mock_token_response.status = 200
    mock_token_response.json = AsyncMock(return_value={"token": "http-token-123"})
    mock_token_response.__aenter__ = AsyncMock(return_value=mock_token_response)
    mock_token_response.__aexit__ = AsyncMock(return_value=None)

    mock_health_response = AsyncMock()
    mock_health_response.status = 200
    mock_health_response.json = AsyncMock(return_value={"connections": ["executor"]})
    mock_health_response.__aenter__ = AsyncMock(return_value=mock_health_response)
    mock_health_response.__aexit__ = AsyncMock(return_value=None)

    mock_ws = AsyncMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=None)
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock(
        return_value='{"status": "success", "order_id": "test-uuid", "data": {"filled": 100}}'
    )

    mock_session = AsyncMock()
    mock_session.get = MagicMock(
        side_effect=[mock_health_response, mock_token_response]
    )
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_config = Mock()
    mock_config.use_https = False
    mock_config.verify_ssl = True
    mock_config.proxy_url = "http://localhost:8000"
    mock_config.ws_url = "ws://localhost:8000"
    mock_config.ws_path = "/ws"
    mock_config.token_url = "http://localhost:8000/token"
    mock_config.username = "testuser"
    mock_config.password = "testpass"
    mock_config.timeout = 30

    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch("websockets.connect", return_value=mock_ws) as mock_ws_connect:
            with patch("trader_initiator.client._get_ssl_context") as mock_get_ssl:
                with patch(
                    "trader_initiator.client.generate_order_id",
                    return_value="test-order-id",
                ):
                    mock_get_ssl.return_value = None

                    result = await send_order(
                        "000001.SZ", "buy", 10.5, 100, mock_config
                    )

                    assert result["status"] == "success"
                    assert result["order_id"] == "test-uuid"
                    # Verify WebSocket URL uses ws://
                    ws_call_args = mock_ws_connect.call_args[0]
                    assert ws_call_args[0].startswith("ws://")


# ==================== HTTPS Protocol Tests ====================


@pytest.mark.asyncio
async def test_get_token_https():
    """Test get_token with HTTPS protocol (with SSL verification)."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"token": "secure-token-456"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = True
    mock_config.token_url = "https://localhost:8443/token"
    mock_config.username = "testuser"
    mock_config.password = "testpass"

    mock_ssl_context = ssl.create_default_context()

    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_session_cls:
        with patch("trader_initiator.client._get_ssl_context") as mock_get_ssl:
            mock_get_ssl.return_value = mock_ssl_context

            token = await get_token(mock_config)

            assert token == "secure-token-456"
            # Verify SSL context was called
            mock_get_ssl.assert_called_once_with(mock_config)
            # Verify connector was created with SSL context
            call_args = mock_session_cls.call_args
            if hasattr(call_args, "kwargs"):
                connector = call_args.kwargs.get("connector")
            else:
                connector = call_args[1].get("connector")
            assert connector is not None


@pytest.mark.asyncio
async def test_get_token_https_no_verify():
    """Test token retrieval with HTTPS but no certificate verification."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"token": "unverified_token"})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = False
    mock_config.token_url = "https://self-signed:8443/token"
    mock_config.username = "initiator"
    mock_config.password = "secret"

    with patch("aiohttp.ClientSession", return_value=mock_session) as mock_session_cls:
        with patch("trader_initiator.client._get_ssl_context") as mock_get_ssl:
            mock_ssl_context = ssl._create_unverified_context()
            mock_get_ssl.return_value = mock_ssl_context

            token = await get_token(mock_config)

            assert token == "unverified_token"
            # Verify SSL context was passed
            mock_session_cls.assert_called_once()
            call_kwargs = (
                mock_session_cls.call_args.kwargs
                if hasattr(mock_session_cls.call_args, "kwargs")
                else mock_session_cls.call_args[1]
            )
            assert call_kwargs.get("connector") is not None


@pytest.mark.asyncio
async def test_send_order_https_success():
    """Test successful order execution with HTTPS protocol."""
    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = True
    mock_config.proxy_url = "https://localhost:8443"
    mock_config.token_url = "https://localhost:8443/token"
    mock_config.ws_url = "wss://localhost:8443"
    mock_config.ws_path = "/ws"
    mock_config.username = "initiator"
    mock_config.password = "secret"
    mock_config.timeout = 30

    mock_ssl_context = ssl.create_default_context()

    # Mock token response
    mock_token_response = AsyncMock()
    mock_token_response.status = 200
    mock_token_response.json = AsyncMock(return_value={"token": "test_token_123"})
    mock_token_response.__aenter__ = AsyncMock(return_value=mock_token_response)
    mock_token_response.__aexit__ = AsyncMock(return_value=None)

    # Mock health check response
    mock_health_response = AsyncMock()
    mock_health_response.status = 200
    mock_health_response.json = AsyncMock(return_value={"connections": ["executor"]})
    mock_health_response.__aenter__ = AsyncMock(return_value=mock_health_response)
    mock_health_response.__aexit__ = AsyncMock(return_value=None)

    # Mock WebSocket
    mock_websocket = AsyncMock()
    mock_websocket.recv = AsyncMock(
        return_value='{"status": "success", "order_id": "test-uuid", "data": {"filled": 100}}'
    )
    mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
    mock_websocket.__aexit__ = AsyncMock(return_value=None)

    # Mock session
    mock_session = AsyncMock()
    mock_session.get = MagicMock(
        side_effect=[mock_health_response, mock_token_response]
    )
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "trader_initiator.client._get_ssl_context", return_value=mock_ssl_context
    ):
        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("websockets.connect", return_value=mock_websocket):
                with patch(
                    "trader_initiator.client.generate_order_id",
                    return_value="test-uuid",
                ):
                    result = await send_order(
                        "000001.SZ", "buy", 10.5, 100, mock_config
                    )

                    assert result["status"] == "success"
                    assert result["order_id"] == "test-uuid"


@pytest.mark.asyncio
async def test_send_order_https_without_verification():
    """Test send_order with HTTPS but without certificate verification."""
    mock_token_response = AsyncMock()
    mock_token_response.status = 200
    mock_token_response.json = AsyncMock(return_value={"token": "unverified-token"})
    mock_token_response.__aenter__ = AsyncMock(return_value=mock_token_response)
    mock_token_response.__aexit__ = AsyncMock(return_value=None)

    mock_health_response = AsyncMock()
    mock_health_response.status = 200
    mock_health_response.json = AsyncMock(return_value={"connections": ["executor"]})
    mock_health_response.__aenter__ = AsyncMock(return_value=mock_health_response)
    mock_health_response.__aexit__ = AsyncMock(return_value=None)

    mock_ws = AsyncMock()
    mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
    mock_ws.__aexit__ = AsyncMock(return_value=None)
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock(
        return_value='{"status": "success", "order_id": "test-uuid-3"}'
    )

    mock_session = AsyncMock()
    mock_session.get = MagicMock(
        side_effect=[mock_health_response, mock_token_response]
    )
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = False  # Self-signed cert
    mock_config.proxy_url = "https://localhost:8443"
    mock_config.ws_url = "wss://localhost:8443"
    mock_config.ws_path = "/ws"
    mock_config.token_url = "https://localhost:8443/token"
    mock_config.username = "testuser"
    mock_config.password = "testpass"
    mock_config.timeout = 30

    unverified_ssl_context = ssl._create_unverified_context()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        with patch("websockets.connect", return_value=mock_ws) as mock_ws_connect:
            with patch(
                "trader_initiator.client._get_ssl_context",
                return_value=unverified_ssl_context,
            ) as mock_get_ssl:
                with patch(
                    "trader_initiator.client.generate_order_id",
                    return_value="test-order-id-3",
                ):
                    result = await send_order(
                        "000001.SZ", "buy", 15.0, 500, mock_config
                    )

                    assert result["status"] == "success"
                    # Verify unverified SSL context was used
                    mock_get_ssl.assert_called_with(mock_config)
                    # Verify SSL context passed to websockets
                    ws_call_args = mock_ws_connect.call_args
                    ws_kwargs = (
                        ws_call_args.kwargs
                        if hasattr(ws_call_args, "kwargs")
                        else ws_call_args[1]
                    )
                    passed_ssl = ws_kwargs.get("ssl")
                    assert passed_ssl is not None
                    assert passed_ssl.verify_mode == ssl.CERT_NONE


@pytest.mark.asyncio
async def test_send_order_https_no_verify():
    """Test successful order execution with HTTPS but no SSL verification."""
    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = False  # Self-signed cert
    mock_config.proxy_url = "https://localhost:8443"
    mock_config.token_url = "https://localhost:8443/token"
    mock_config.ws_url = "wss://localhost:8443"
    mock_config.ws_path = "/ws"
    mock_config.username = "initiator"
    mock_config.password = "secret"
    mock_config.timeout = 30

    mock_ssl_context = ssl._create_unverified_context()

    # Mock token response
    mock_token_response = AsyncMock()
    mock_token_response.status = 200
    mock_token_response.json = AsyncMock(return_value={"token": "test_token_456"})
    mock_token_response.__aenter__ = AsyncMock(return_value=mock_token_response)
    mock_token_response.__aexit__ = AsyncMock(return_value=None)

    # Mock health check response
    mock_health_response = AsyncMock()
    mock_health_response.status = 200
    mock_health_response.json = AsyncMock(return_value={"connections": ["executor"]})
    mock_health_response.__aenter__ = AsyncMock(return_value=mock_health_response)
    mock_health_response.__aexit__ = AsyncMock(return_value=None)

    # Mock WebSocket
    mock_websocket = AsyncMock()
    mock_websocket.recv = AsyncMock(
        return_value='{"status": "success", "order_id": "test-uuid-2", "data": {"filled": 200}}'
    )
    mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
    mock_websocket.__aexit__ = AsyncMock(return_value=None)

    # Mock session
    mock_session = AsyncMock()
    mock_session.get = MagicMock(
        side_effect=[mock_health_response, mock_token_response]
    )
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "trader_initiator.client._get_ssl_context", return_value=mock_ssl_context
    ):
        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("websockets.connect", return_value=mock_websocket):
                with patch(
                    "trader_initiator.client.generate_order_id",
                    return_value="test-uuid-2",
                ):
                    result = await send_order(
                        "600000.SH", "sell", 20.0, 200, mock_config
                    )

                    assert result["status"] == "success"
                    assert result["order_id"] == "test-uuid-2"


@pytest.mark.asyncio
async def test_get_token_https_connection_error():
    """Test token retrieval failure with HTTPS connection error."""
    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = True
    mock_config.token_url = "https://localhost:8443/token"
    mock_config.username = "initiator"
    mock_config.password = "secret"

    mock_ssl_context = ssl.create_default_context()

    # Simulate connection error
    with patch(
        "trader_initiator.client._get_ssl_context", return_value=mock_ssl_context
    ):
        with patch(
            "aiohttp.ClientSession",
            side_effect=aiohttp.ClientError("SSL handshake failed"),
        ):
            with pytest.raises(ConnectionError, match="Failed to get token"):
                await get_token(mock_config)


@pytest.mark.asyncio
async def test_check_executor_online_https():
    """Test executor online check with HTTPS protocol."""
    mock_config = Mock()
    mock_config.use_https = True
    mock_config.verify_ssl = True
    mock_config.proxy_url = "https://localhost:8443"

    mock_ssl_context = ssl.create_default_context()

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"connections": ["initiator", "executor"]}
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = AsyncMock()
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "trader_initiator.client._get_ssl_context", return_value=mock_ssl_context
    ):
        with patch(
            "aiohttp.ClientSession", return_value=mock_session
        ) as mock_session_cls:
            result = await check_executor_online(mock_config)

            assert result is True

            # Verify SSL context was passed
            mock_session_cls.assert_called_once()
            call_kwargs = mock_session_cls.call_args.kwargs
            assert "connector" in call_kwargs
