"""Unit tests for qmt_proxy connection_manager module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from qmt_proxy.connection_manager import (
    ConnectionManager,
    ROLE_EXECUTOR,
    ROLE_INITIATOR,
)
from qmt_proxy.exceptions import ConnectionManagerError


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


class TestConnectionManager:
    """Test cases for ConnectionManager class."""

    @pytest.mark.asyncio
    async def test_connect_initiator(self, mock_websocket) -> None:
        """Test connecting an initiator."""
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        assert ConnectionManager.is_initiator_connected()
        assert ConnectionManager.get_connection_count() == 1

    @pytest.mark.asyncio
    async def test_connect_executor(self, mock_websocket) -> None:
        """Test connecting an executor."""
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        assert ConnectionManager.is_executor_connected()
        assert ConnectionManager.get_connection_count() == 1

    @pytest.mark.asyncio
    async def test_connect_invalid_role(self, mock_websocket) -> None:
        """Test connecting with invalid role."""
        with pytest.raises(ConnectionManagerError) as exc_info:
            await ConnectionManager.connect("invalid_role", mock_websocket)
        assert "Invalid role" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_duplicate_role(self, mock_websocket) -> None:
        """Test connecting the same role twice."""
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        with pytest.raises(ConnectionManagerError) as exc_info:
            await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        assert "Connection already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disconnect_initiator(self, mock_websocket) -> None:
        """Test disconnecting initiator."""
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        await ConnectionManager.disconnect(ROLE_INITIATOR)
        assert not ConnectionManager.is_initiator_connected()
        assert ConnectionManager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_executor(self, mock_websocket) -> None:
        """Test disconnecting executor."""
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        await ConnectionManager.disconnect(ROLE_EXECUTOR)
        assert not ConnectionManager.is_executor_connected()
        assert ConnectionManager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_non_existent(self) -> None:
        """Test disconnecting a role that doesn't exist."""
        # Should not raise
        await ConnectionManager.disconnect("initiator")

    @pytest.mark.asyncio
    async def test_send_to_executor(self, mock_websocket) -> None:
        """Test sending message to executor."""
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        message = {"stock": "000001.SH", "action": "buy", "price": 20, "number": 1000}
        await ConnectionManager.send_to_executor(message)
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_executor_not_connected(self, mock_websocket) -> None:
        """Test sending to executor when not connected."""
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        message = {"stock": "000001.SH", "action": "buy", "price": 20, "number": 1000}
        with pytest.raises(ConnectionManagerError) as exc_info:
            await ConnectionManager.send_to_executor(message)
        assert "Executor not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_to_initiator(self, mock_websocket) -> None:
        """Test sending message to initiator."""
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        message = {"status": "success", "data": {"stock": "000001.SH"}}
        await ConnectionManager.send_to_initiator(message)
        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_initiator_not_connected(self, mock_websocket) -> None:
        """Test sending to initiator when not connected."""
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        message = {"status": "success", "data": {"stock": "000001.SH"}}
        with pytest.raises(ConnectionManagerError) as exc_info:
            await ConnectionManager.send_to_initiator(message)
        assert "Initiator not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_to_executor_websocket_error(self, mock_websocket) -> None:
        """Test handling WebSocket error when sending to executor."""
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        mock_websocket.send_json.side_effect = Exception("WebSocket error")
        message = {"stock": "000001.SH", "action": "buy", "price": 20, "number": 1000}
        with pytest.raises(ConnectionManagerError) as exc_info:
            await ConnectionManager.send_to_executor(message)
        assert "Failed to send message to executor" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_to_initiator_websocket_error(self, mock_websocket) -> None:
        """Test handling WebSocket error when sending to initiator."""
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        mock_websocket.send_json.side_effect = Exception("WebSocket error")
        message = {"status": "success", "data": {"stock": "000001.SH"}}
        with pytest.raises(ConnectionManagerError) as exc_info:
            await ConnectionManager.send_to_initiator(message)
        assert "Failed to send message to initiator" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_is_executor_connected(self, mock_websocket) -> None:
        """Test checking if executor is connected."""
        assert not ConnectionManager.is_executor_connected()
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        assert ConnectionManager.is_executor_connected()

    @pytest.mark.asyncio
    async def test_is_initiator_connected(self, mock_websocket) -> None:
        """Test checking if initiator is connected."""
        assert not ConnectionManager.is_initiator_connected()
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        assert ConnectionManager.is_initiator_connected()

    @pytest.mark.asyncio
    async def test_get_connection_count(self, mock_websocket) -> None:
        """Test getting connection count."""
        assert ConnectionManager.get_connection_count() == 0
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        assert ConnectionManager.get_connection_count() == 1
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        assert ConnectionManager.get_connection_count() == 2

    @pytest.mark.asyncio
    async def test_get_connected_roles(self, mock_websocket) -> None:
        """Test getting list of connected roles."""
        assert ConnectionManager.get_connected_roles() == []
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        assert ConnectionManager.get_connected_roles() == [ROLE_INITIATOR]
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        roles = ConnectionManager.get_connected_roles()
        assert ROLE_INITIATOR in roles
        assert ROLE_EXECUTOR in roles

    @pytest.mark.asyncio
    async def test_message_flow_between_connections(self, mock_websocket) -> None:
        """Test message flow between initiator and executor."""
        initiator_ws = mock_websocket
        executor_ws = AsyncMock()
        executor_ws.send_json = AsyncMock()

        # Connect both
        await ConnectionManager.connect(ROLE_INITIATOR, initiator_ws)
        await ConnectionManager.connect(ROLE_EXECUTOR, executor_ws)

        # Send from initiator to executor
        message = {"stock": "000001.SH", "action": "buy", "price": 20, "number": 1000}
        await ConnectionManager.send_to_executor(message)
        executor_ws.send_json.assert_called_once_with(message)

        # Send from executor to initiator
        result = {"status": "success", "data": {"stock": "000001.SH", "price": 19.60}}
        await ConnectionManager.send_to_initiator(result)
        initiator_ws.send_json.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self, mock_websocket) -> None:
        """Test reconnecting after disconnect."""
        # Connect and disconnect
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        await ConnectionManager.disconnect(ROLE_INITIATOR)

        # Reconnect with same role
        new_ws = AsyncMock()
        new_ws.send_json = AsyncMock()
        await ConnectionManager.connect(ROLE_INITIATOR, new_ws)
        assert ConnectionManager.is_initiator_connected()


class TestClearAllConnections:
    """Test cases for clear_all_connections function."""

    @pytest.mark.asyncio
    async def test_clear_all_connections(self, mock_websocket) -> None:
        """Test clearing all connections."""
        await ConnectionManager.connect(ROLE_INITIATOR, mock_websocket)
        await ConnectionManager.connect(ROLE_EXECUTOR, mock_websocket)
        assert ConnectionManager.get_connection_count() == 2

        ConnectionManager.clear_all_connections()

        assert ConnectionManager.get_connection_count() == 0
        assert not ConnectionManager.is_initiator_connected()
        assert not ConnectionManager.is_executor_connected()

    @pytest.mark.asyncio
    async def test_clear_empty_connections(self) -> None:
        """Test clearing connections when none exist."""
        assert ConnectionManager.get_connection_count() == 0
        ConnectionManager.clear_all_connections()  # Should not raise
        assert ConnectionManager.get_connection_count() == 0
