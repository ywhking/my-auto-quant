"""Tests for HTTPS/SSL functionality in trader_executor."""

import ssl
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from trader_executor.client import ExecutorClient

from trader_executor.config import ExecutorConfig


@pytest.fixture
def reset_config():
    """Reset ExecutorConfig singleton before each test."""
    ExecutorConfig._config_data = {}
    ExecutorConfig._instance = None
    yield
    # Cleanup after test
    ExecutorConfig._config_data = {}
    ExecutorConfig._instance = None


@pytest.fixture
def fresh_config(reset_config):
    """Create a fresh ExecutorConfig instance for testing."""
    config = ExecutorConfig()
    # Set default test values that match test expectations
    config._config_data["proxy"] = {
        "host": "localhost",
        "port": 8000,
        "ws_path": "/ws",
        "token_path": "/token",
        "use_ssl": False,
        "ssl_verify": True,
        "ssl_cert_path": None,
        "ssl_key_path": None,
        "ssl_ca_path": None,
    }
    return config


class TestHTTPSConfig:
    """Test cases for HTTPS/SSL configuration."""

    def test_ssl_config_defaults(self, fresh_config) -> None:
        """Test default SSL configuration values."""
        config = fresh_config
        assert config.use_ssl is False
        assert config.ssl_verify is True
        assert config.ssl_cert_path is None
        assert config.ssl_key_path is None
        assert config.ssl_ca_path is None

    def test_ssl_config_custom_values(self, fresh_config) -> None:
        """Test custom SSL configuration values."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = True
        config._config_data["proxy"]["ssl_verify"] = False
        config._config_data["proxy"]["ssl_cert_path"] = "/path/to/cert.pem"
        config._config_data["proxy"]["ssl_key_path"] = "/path/to/key.pem"
        config._config_data["proxy"]["ssl_ca_path"] = "/path/to/ca.pem"

        assert config.use_ssl is True
        assert config.ssl_verify is False
        assert config.ssl_cert_path == "/path/to/cert.pem"
        assert config.ssl_key_path == "/path/to/key.pem"
        assert config.ssl_ca_path == "/path/to/ca.pem"

    def test_http_url_without_ssl(self, fresh_config) -> None:
        """Test HTTP URL generation without SSL."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = False
        config._config_data["proxy"]["host"] = "localhost"
        config._config_data["proxy"]["port"] = 8000

        assert config.proxy_url == "http://localhost:8000"
        assert config.ws_url == "ws://localhost:8000"
        assert config.token_url == "http://localhost:8000/token"

    def test_https_url_with_ssl(self, fresh_config) -> None:
        """Test HTTPS URL generation with SSL enabled."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = True
        config._config_data["proxy"]["host"] = "secure.example.com"
        config._config_data["proxy"]["port"] = 8443

        assert config.proxy_url == "https://secure.example.com:8443"
        assert config.ws_url == "wss://secure.example.com:8443"
        assert config.token_url == "https://secure.example.com:8443/token"

    def test_get_ssl_context_returns_none_when_ssl_disabled(self, fresh_config) -> None:
        """Test that get_ssl_context returns None when SSL is disabled."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = False

        ssl_context = config.get_ssl_context()
        assert ssl_context is None

    def test_get_ssl_context_with_default_settings(self, fresh_config) -> None:
        """Test SSL context creation with default settings."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = True
        config._config_data["proxy"]["ssl_verify"] = True

        ssl_context = config.get_ssl_context()
        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)
        assert ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert ssl_context.check_hostname is True

    def test_get_ssl_context_with_disabled_verification(self, fresh_config) -> None:
        """Test SSL context creation with verification disabled."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = True
        config._config_data["proxy"]["ssl_verify"] = False

        ssl_context = config.get_ssl_context()
        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)
        assert ssl_context.verify_mode == ssl.CERT_NONE
        assert ssl_context.check_hostname is False

    def test_get_ssl_context_with_custom_ca(self, fresh_config) -> None:
        """Test SSL context creation with custom CA certificate."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = True
        config._config_data["proxy"]["ssl_verify"] = True
        config._config_data["proxy"]["ssl_ca_path"] = "/path/to/ca.pem"

        # Mock the CA file existence check by patching create_default_context
        with patch("ssl.create_default_context") as mock_create_ctx:
            mock_context = MagicMock()
            mock_create_ctx.return_value = mock_context

            ssl_context = config.get_ssl_context()
            mock_create_ctx.assert_called_once_with(cafile="/path/to/ca.pem")

    def test_get_ssl_context_with_client_cert(self, fresh_config) -> None:
        """Test SSL context creation with client certificate."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = True
        config._config_data["proxy"]["ssl_cert_path"] = "/path/to/cert.pem"
        config._config_data["proxy"]["ssl_key_path"] = "/path/to/key.pem"

        # Mock the load_cert_chain method to avoid file not found error
        with patch.object(ssl.SSLContext, "load_cert_chain") as mock_load_cert:
            ssl_context = config.get_ssl_context()
            assert ssl_context is not None
            # Verify that load_cert_chain was called with the correct paths
            mock_load_cert.assert_called_once_with(
                certfile="/path/to/cert.pem",
                keyfile="/path/to/key.pem",
            )


class TestHTTPSClient:
    """Test cases for HTTPS client functionality."""

    @pytest.fixture
    def client_with_ssl_config(self, reset_config):
        """Create a client with SSL configuration."""
        config = ExecutorConfig()
        config._config_data["proxy"] = {
            "host": "localhost",
            "port": 8000,
            "ws_path": "/ws",
            "token_path": "/token",
            "use_ssl": True,
            "ssl_verify": False,  # Disable for tests
            "ssl_cert_path": None,
            "ssl_key_path": None,
            "ssl_ca_path": None,
        }
        config._config_data["auth"] = {
            "username": "test",
            "password": "test",
        }
        config._config_data["allow_mock"] = True
        return ExecutorClient(config)

    @pytest.mark.asyncio
    async def test_get_token_with_https(self, client_with_ssl_config) -> None:
        """Test token retrieval over HTTPS."""
        client = client_with_ssl_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"token": "secure-token-123"})

        mock_get_response = AsyncMock()
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_connector = MagicMock()

        with patch("trader_executor.client.aiohttp.TCPConnector") as mock_tcp_connector:
            with patch(
                "trader_executor.client.aiohttp.ClientSession"
            ) as mock_client_session:
                mock_tcp_connector.return_value = mock_connector
                mock_client_session.return_value = mock_session

                token = await client._get_token()
                assert token == "secure-token-123"

                # Verify that TCPConnector was called (indicating SSL is being used)
                mock_tcp_connector.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_with_https_disabled_verify(
        self, client_with_ssl_config
    ) -> None:
        """Test token retrieval over HTTPS with verification disabled."""
        client = client_with_ssl_config

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"token": "insecure-token-456"})

        mock_get_response = AsyncMock()
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_connector = MagicMock()

        with patch("trader_executor.client.aiohttp.TCPConnector") as mock_tcp_connector:
            with patch(
                "trader_executor.client.aiohttp.ClientSession"
            ) as mock_client_session:
                mock_tcp_connector.return_value = mock_connector
                mock_client_session.return_value = mock_session

                token = await client._get_token()
                assert token == "insecure-token-456"

    @pytest.mark.asyncio
    async def test_websocket_connection_with_ssl(self, client_with_ssl_config) -> None:
        """Test WebSocket connection with SSL."""
        client = client_with_ssl_config

        # Mock the _get_token method
        client._get_token = AsyncMock(return_value="test-token")

        mock_websocket = AsyncMock()
        mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_websocket.__aexit__ = AsyncMock(return_value=None)
        mock_websocket.close = AsyncMock()

        with patch("trader_executor.client.websockets.connect") as mock_connect:
            mock_connect.return_value = mock_websocket

            # Mock _message_loop to prevent infinite loop
            client._message_loop = AsyncMock()

            await client._connect_and_run()

            # Verify websockets.connect was called with ssl parameter
            mock_connect.assert_called_once()
            call_kwargs = mock_connect.call_args.kwargs
            assert "ssl" in call_kwargs

    @pytest.mark.asyncio
    async def test_websocket_connection_without_ssl(self, reset_config) -> None:
        """Test WebSocket connection without SSL."""
        config = ExecutorConfig()
        config._config_data["proxy"] = {
            "host": "localhost",
            "port": 8000,
            "ws_path": "/ws",
            "token_path": "/token",
            "use_ssl": False,
            "ssl_verify": True,
            "ssl_cert_path": None,
            "ssl_key_path": None,
            "ssl_ca_path": None,
        }
        config._config_data["allow_mock"] = True
        client = ExecutorClient(config)

        # Mock the _get_token method
        client._get_token = AsyncMock(return_value="test-token")

        mock_websocket = AsyncMock()
        mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_websocket.__aexit__ = AsyncMock(return_value=None)
        mock_websocket.close = AsyncMock()

        with patch("trader_executor.client.websockets.connect") as mock_connect:
            mock_connect.return_value = mock_websocket

            # Mock _message_loop to prevent infinite loop
            client._message_loop = AsyncMock()

            await client._connect_and_run()

            # Verify websockets.connect was called
            mock_connect.assert_called_once()
            call_kwargs = mock_connect.call_args.kwargs
            assert "ssl" in call_kwargs


class TestSSLIntegration:
    """Integration tests for SSL functionality."""

    def test_full_https_config_integration(self, reset_config) -> None:
        """Test full HTTPS configuration with all SSL options."""
        config = ExecutorConfig()
        config._config_data["proxy"] = {
            "host": "api.trading.com",
            "port": 443,
            "ws_path": "/ws",
            "token_path": "/auth",
            "use_ssl": True,
            "ssl_verify": True,
            "ssl_cert_path": "/etc/ssl/client.crt",
            "ssl_key_path": "/etc/ssl/client.key",
            "ssl_ca_path": "/etc/ssl/ca.crt",
        }

        # Verify URLs are HTTPS/WSS
        assert config.proxy_url == "https://api.trading.com:443"
        assert config.ws_url == "wss://api.trading.com:443"
        assert config.token_url == "https://api.trading.com:443/auth"

        # Verify SSL settings
        assert config.use_ssl is True
        assert config.ssl_verify is True
        assert config.ssl_cert_path == "/etc/ssl/client.crt"
        assert config.ssl_key_path == "/etc/ssl/client.key"
        assert config.ssl_ca_path == "/etc/ssl/ca.crt"

    def test_ssl_context_with_all_options(self, fresh_config) -> None:
        """Test SSL context creation with all options enabled."""
        config = fresh_config
        config._config_data["proxy"]["use_ssl"] = True
        config._config_data["proxy"]["ssl_verify"] = True
        config._config_data["proxy"]["ssl_ca_path"] = None  # Use default CA

        ssl_context = config.get_ssl_context()

        assert ssl_context is not None
        assert isinstance(ssl_context, ssl.SSLContext)

    @pytest.mark.asyncio
    async def test_client_initialization_with_ssl_config(self, reset_config) -> None:
        """Test client initialization with SSL configuration."""
        config = ExecutorConfig()
        config._config_data["proxy"] = {
            "host": "secure.proxy.com",
            "port": 9443,
            "ws_path": "/ws",
            "token_path": "/token",
            "use_ssl": True,
            "ssl_verify": False,
            "ssl_cert_path": None,
            "ssl_key_path": None,
            "ssl_ca_path": None,
        }
        config._config_data["allow_mock"] = True

        client = ExecutorClient(config)

        assert client.config.use_ssl is True
        assert "wss://" in client.config.ws_url
        assert "https://" in client.config.proxy_url
