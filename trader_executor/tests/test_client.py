"""Tests for ExecutorClient in trader_executor."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from trader_executor.client import ExecutorClient

from trader_executor.exceptions import QMTConnectionError


class TestExecutorClient:
    """Test cases for ExecutorClient class."""

    def test_initialization(self, mock_config) -> None:
        """Test client initialization."""
        client = ExecutorClient(mock_config)
        assert client.config is not None
        assert client.qmt_client is not None
        assert not client.is_running

    def test_initialization_with_config(self, mock_config) -> None:
        """Test client initialization with custom config."""
        from trader_executor.config import ExecutorConfig

        config = ExecutorConfig()
        config._config_data["allow_mock"] = True
        client = ExecutorClient(config)
        assert client.config is config

    @pytest.mark.asyncio
    async def test_get_token_success(self) -> None:
        """Test successful token retrieval."""
        client = ExecutorClient()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"token": "test-token-123"})

        mock_get_response = AsyncMock()
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("trader_executor.client.aiohttp.ClientSession") as mock_client:
            mock_client.return_value = mock_session

            token = await client._get_token()
            assert token == "test-token-123"

    @pytest.mark.asyncio
    async def test_get_token_auth_failure(self) -> None:
        """Test token retrieval with authentication failure."""
        client = ExecutorClient()

        mock_response = AsyncMock()
        mock_response.status = 401

        mock_get_response = AsyncMock()
        mock_get_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_get_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("trader_executor.client.aiohttp.ClientSession") as mock_client:
            mock_client.return_value = mock_session

            with pytest.raises(ConnectionError) as exc_info:
                await client._get_token()

            assert "authentication failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_process_message_success(self, valid_trading_message: dict) -> None:
        """Test processing a valid trading message."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client._subscribed = True

        # Mock risk checker to pass
        client.risk_checker.check_all = MagicMock(return_value=(True, None))

        # Mock qmt_client.place_order
        client.qmt_client.place_order = AsyncMock(return_value=123456)

        mock_websocket = AsyncMock()

        message = json.dumps(valid_trading_message)
        await client._process_message(message, mock_websocket)

        # Verify order was placed
        client.qmt_client.place_order.assert_called_once_with(
            valid_trading_message["stock"],
            valid_trading_message["action"],
            valid_trading_message["price"],
            valid_trading_message["number"],
        )

        # Verify response was sent
        assert mock_websocket.send.called
        response_data = json.loads(mock_websocket.send.call_args[0][0])
        assert response_data["status"] == "success"
        assert response_data["order_id"] == "123456"
    async def test_process_message_success(self, valid_trading_message: dict) -> None:
        """Test processing a valid trading message."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client._subscribed = True

        # Mock qmt_client.place_order
        client.qmt_client.place_order = AsyncMock(return_value=123456)

        mock_websocket = AsyncMock()

        message = json.dumps(valid_trading_message)
        await client._process_message(message, mock_websocket)

        # Verify order was placed
        client.qmt_client.place_order.assert_called_once_with(
            valid_trading_message["stock"],
            valid_trading_message["action"],
            valid_trading_message["price"],
            valid_trading_message["number"],
        )

        # Verify response was sent
        assert mock_websocket.send.called
        response_data = json.loads(mock_websocket.send.call_args[0][0])
        assert response_data["status"] == "success"
        assert response_data["order_id"] == "123456"

    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self) -> None:
        """Test processing invalid JSON message."""
        client = ExecutorClient()
        mock_websocket = AsyncMock()

        await client._process_message("invalid json{{{", mock_websocket)

        # Verify error response was sent
        assert mock_websocket.send.called
        response_data = json.loads(mock_websocket.send.call_args[0][0])
        assert response_data["status"] == "error"
        assert "invalid json" in response_data["message"].lower()

    @pytest.mark.asyncio
    async def test_process_message_validation_error(
        self, invalid_trading_message: dict
    ) -> None:
        """Test processing message with validation error."""
        client = ExecutorClient()
        mock_websocket = AsyncMock()

        message = json.dumps(invalid_trading_message)
        await client._process_message(message, mock_websocket)

        # Verify error response was sent
        assert mock_websocket.send.called
        response_data = json.loads(mock_websocket.send.call_args[0][0])
        assert response_data["status"] == "error"
        assert "validation error" in response_data["message"].lower()

    @pytest.mark.asyncio
    async def test_process_message_qmt_error(self, valid_trading_message: dict) -> None:
        """Test processing message when QMT fails."""
        client = ExecutorClient()
        client.qmt_client._connected = True

        # Mock risk checker to pass
        client.risk_checker.check_all = MagicMock(return_value=(True, None))

        # Mock qmt_client.place_order to raise exception
        client.qmt_client.place_order = AsyncMock(
            side_effect=QMTConnectionError("QMT not connected")
        )

        mock_websocket = AsyncMock()

        message = json.dumps(valid_trading_message)
        await client._process_message(message, mock_websocket)

        # Verify error response was sent
        assert mock_websocket.send.called
        response_data = json.loads(mock_websocket.send.call_args[0][0])
        assert response_data["status"] == "error"
        assert "qmt" in response_data["message"].lower()
    async def test_process_message_qmt_error(self, valid_trading_message: dict) -> None:
        """Test processing message when QMT fails."""
        client = ExecutorClient()
        client.qmt_client._connected = True

        # Mock qmt_client.place_order to raise exception
        client.qmt_client.place_order = AsyncMock(
            side_effect=QMTConnectionError("QMT not connected")
        )

        mock_websocket = AsyncMock()

        message = json.dumps(valid_trading_message)
        await client._process_message(message, mock_websocket)

        # Verify error response was sent
        assert mock_websocket.send.called
        response_data = json.loads(mock_websocket.send.call_args[0][0])
        assert response_data["status"] == "error"
        assert "qmt" in response_data["message"].lower()

    @pytest.mark.asyncio
    async def test_reconnect_delay(self) -> None:
        """Test reconnect delay calculation."""
        client = ExecutorClient()

        # First attempt: should be 1 second
        client._reconnect_attempts = 0
        start = asyncio.get_event_loop().time()
        await client._reconnect_delay()
        elapsed = asyncio.get_event_loop().time() - start
        assert 0.9 < elapsed < 1.5  # Allow some tolerance

        # Second attempt: should be 2 seconds
        client._reconnect_attempts = 1
        start = asyncio.get_event_loop().time()
        await client._reconnect_delay()
        elapsed = asyncio.get_event_loop().time() - start
        assert 1.9 < elapsed < 2.5

    @pytest.mark.asyncio
    async def test_should_reconnect_within_limit(self) -> None:
        """Test should_reconnect within max attempts."""
        client = ExecutorClient()
        client._reconnect_attempts = 5
        client.config._config_data["connection"]["max_reconnect_attempts"] = 10

        result = await client._should_reconnect()
        assert result is True

    @pytest.mark.asyncio
    async def test_should_reconnect_exceeds_limit(self) -> None:
        """Test should_reconnect exceeds max attempts."""
        client = ExecutorClient()
        client._reconnect_attempts = 10
        client.config._config_data["connection"]["max_reconnect_attempts"] = 10

        result = await client._should_reconnect()
        assert result is False

    @pytest.mark.asyncio
    async def test_should_reconnect_when_stopped(self) -> None:
        """Test should_reconnect when client is stopped."""
        client = ExecutorClient()
        client._stop_event.set()

        result = await client._should_reconnect()
        assert result is False
    @pytest.mark.asyncio
    async def test_start_qmt_connect_failure(self) -> None:
        """Test start when QMT connection fails (no retry in client)."""
        client = ExecutorClient()

        # Mock qmt_client.connect to raise exception
        client.qmt_client.connect = AsyncMock(
            side_effect=QMTConnectionError("QMT connection failed")
        )

        with pytest.raises(QMTConnectionError):
            await client.start()

        assert not client.is_running

    @pytest.mark.asyncio
    async def test_stop(self) -> None:
        """Test stopping the client."""
        client = ExecutorClient()
        client.is_running = True
        client._stop_event.clear()

        # Mock qmt_client.disconnect
        client.qmt_client.disconnect = AsyncMock()

        await client.stop()

        assert not client.is_running
        assert client._stop_event.is_set()
        client.qmt_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_websocket(self) -> None:
        """Test stopping client with active WebSocket."""
        client = ExecutorClient()
        client.is_running = True
        client.websocket = AsyncMock()
        client._stop_event.clear()

        # Mock qmt_client.disconnect
        client.qmt_client.disconnect = AsyncMock()

        await client.stop()

        assert not client.is_running
        client.websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        client = ExecutorClient()
        client.qmt_client.connect = AsyncMock()
        client._connect_and_run = AsyncMock(side_effect=Exception("Stop loop"))

        # Limit reconnect to prevent infinite loop
        client.config._config_data["connection"]["max_reconnect_attempts"] = 1

        # Context manager should enter and exit cleanly
        async with client:
            assert client.is_running

        assert not client.is_running

    @pytest.mark.asyncio
    async def test_process_message_buy_order(self) -> None:
        """Test processing a buy order."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(return_value=123456)

        # Mock risk checker to pass
        client.risk_checker.check_all = MagicMock(return_value=(True, None))

        mock_websocket = AsyncMock()

        message = json.dumps(
            {"stock": "000001.SH", "action": "buy", "price": 19.60, "number": 1000}
        )
        await client._process_message(message, mock_websocket)

        client.qmt_client.place_order.assert_called_once_with(
            "000001.SH", "buy", 19.60, 1000
        )
    async def test_process_message_buy_order(self) -> None:
        """Test processing a buy order."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(return_value=123456)

        mock_websocket = AsyncMock()

        message = json.dumps(
            {"stock": "000001.SH", "action": "buy", "price": 19.60, "number": 1000}
        )
        await client._process_message(message, mock_websocket)

        client.qmt_client.place_order.assert_called_once_with(
            "000001.SH", "buy", 19.60, 1000
        )

    @pytest.mark.asyncio
    async def test_process_message_sell_order(self) -> None:
        """Test processing a sell order."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(return_value=234567)

        # Mock risk checker to pass
        client.risk_checker.check_all = MagicMock(return_value=(True, None))

        mock_websocket = AsyncMock()

        message = json.dumps(
            {"stock": "600000.SH", "action": "sell", "price": 20.50, "number": 500}
        )
        await client._process_message(message, mock_websocket)

        client.qmt_client.place_order.assert_called_once_with(
            "600000.SH", "sell", 20.50, 500
        )
    async def test_process_message_sell_order(self) -> None:
        """Test processing a sell order."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(return_value=234567)

        mock_websocket = AsyncMock()

        message = json.dumps(
            {"stock": "600000.SH", "action": "sell", "price": 20.50, "number": 500}
        )
        await client._process_message(message, mock_websocket)

        client.qmt_client.place_order.assert_called_once_with(
            "600000.SH", "sell", 20.50, 500
        )

    @pytest.mark.asyncio
    async def test_multiple_messages(self) -> None:
        """Test processing multiple messages sequentially."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(side_effect=[123456, 234567])

        # Mock risk checker to pass
        client.risk_checker.check_all = MagicMock(return_value=(True, None))

        mock_websocket = AsyncMock()

        # First message
        message1 = json.dumps(
            {"stock": "000001.SH", "action": "buy", "price": 19.60, "number": 1000}
        )
        await client._process_message(message1, mock_websocket)

        # Second message
        message2 = json.dumps(
            {"stock": "600000.SH", "action": "sell", "price": 20.50, "number": 500}
        )
        await client._process_message(message2, mock_websocket)

        assert client.qmt_client.place_order.call_count == 2
    async def test_multiple_messages(self) -> None:
        """Test processing multiple messages sequentially."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(side_effect=[123456, 234567])

        mock_websocket = AsyncMock()

        # First message
        message1 = json.dumps(
            {"stock": "000001.SH", "action": "buy", "price": 19.60, "number": 1000}
        )
        await client._process_message(message1, mock_websocket)

        # Second message
        message2 = json.dumps(
            {"stock": "600000.SH", "action": "sell", "price": 20.50, "number": 500}
        )
        await client._process_message(message2, mock_websocket)

        assert client.qmt_client.place_order.call_count == 2

    @pytest.mark.asyncio
    async def test_message_with_different_price_formats(self) -> None:
        """Test processing messages with different price formats."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(return_value=123456)

        # Mock risk checker to pass
        client.risk_checker.check_all = MagicMock(return_value=(True, None))

        mock_websocket = AsyncMock()

        # Integer price
        message1 = json.dumps(
            {"stock": "000001.SH", "action": "buy", "price": 19, "number": 1000}
        )
        await client._process_message(message1, mock_websocket)

        # Float price
        message2 = json.dumps(
            {"stock": "600000.SH", "action": "buy", "price": 19.60, "number": 1000}
        )
        await client._process_message(message2, mock_websocket)
    async def test_message_with_different_price_formats(self) -> None:
        """Test processing messages with different price formats."""
        client = ExecutorClient()
        client.qmt_client._connected = True
        client.qmt_client.place_order = AsyncMock(return_value=123456)

        mock_websocket = AsyncMock()

        # Integer price
        message1 = json.dumps(
            {"stock": "000001.SH", "action": "buy", "price": 19, "number": 1000}
        )
        await client._process_message(message1, mock_websocket)

        # Float price
        message2 = json.dumps(
            {"stock": "600000.SH", "action": "buy", "price": 19.60, "number": 1000}
        )
        await client._process_message(message2, mock_websocket)

        # High precision price
        message3 = json.dumps(
            {"stock": "300001.SZ", "action": "buy", "price": 19.605, "number": 1000}
        )
        await client._process_message(message3, mock_websocket)

        assert client.qmt_client.place_order.call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="WebSocket exception API changed in newer versions")
    async def test_websocket_disconnect_handling(self) -> None:
        """Test handling of WebSocket disconnection."""
        client = ExecutorClient()
        client.qmt_client.connect = AsyncMock()

        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock(
            side_effect=Exception("WebSocket closed")
        )

        with patch("trader_executor.client.websockets.connect") as mock_connect:
            mock_connect.return_value.__aenter__.return_value = mock_websocket

            # Should raise exception
            with pytest.raises(Exception):
                await client._connect_and_run()

    @pytest.mark.asyncio
    async def test_message_loop_stops_on_event(self) -> None:
        """Test that message loop stops when stop event is set."""
        client = ExecutorClient()

        mock_websocket = AsyncMock()
        mock_websocket.recv = AsyncMock(
            return_value='{"stock": "000001.SH", "action": "buy", "price": 19.60, "number": 1000}'
        )

        # Set stop event after first message
        async def side_effect_stop(*args, **kwargs):
            await asyncio.sleep(0.01)
            client._stop_event.set()
            return '{"stock": "000001.SH", "action": "buy", "price": 19.60, "number": 1000}'

        mock_websocket.recv = AsyncMock(side_effect=side_effect_stop)

        # This should not hang
        await client._message_loop(mock_websocket)
