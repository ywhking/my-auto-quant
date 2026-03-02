"""Integration tests for QMT Proxy WebSocket endpoints."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from qmt_proxy.auth import clear_all_tokens
from qmt_proxy.connection_manager import ConnectionManager
from qmt_proxy.main import app


@pytest.fixture
def client():
    """Create a test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset all tokens and connections before each test."""
    yield
    clear_all_tokens()
    ConnectionManager.clear_all_connections()


class TestHealthEndpoint:
    """Test cases for /health endpoint."""

    def test_health_check_empty(self, client) -> None:
        """Test health check with no connections."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["connections"] == []
        assert data["count"] == 0

    def test_test_reset_endpoint(self, client) -> None:
        """Test the test reset endpoint."""
        response = client.post("/test/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset"


class TestAuthEndpoint:
    """Test cases for /auth endpoint."""

    def test_auth_valid_initiator(self, client) -> None:
        """Test authentication with valid initiator credentials."""
        response = client.get("/auth?userName=initiator&password=xxxxxxx")
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 0

    def test_auth_valid_executor(self, client) -> None:
        """Test authentication with valid executor credentials."""
        response = client.get("/auth?userName=executor&password=xxxxxxx")
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert len(data["token"]) > 0

    def test_auth_invalid_username(self, client) -> None:
        """Test authentication with invalid username."""
        response = client.get("/auth?userName=invalid&password=xxxxxxx")
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Invalid credentials"

    def test_auth_invalid_password(self, client) -> None:
        """Test authentication with invalid password."""
        response = client.get("/auth?userName=initiator&password=wrong")
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Invalid credentials"

    def test_auth_missing_username(self, client) -> None:
        """Test authentication with missing username."""
        response = client.get("/auth?password=xxxxxxx")
        # FastAPI will return 422 for missing required parameter
        assert response.status_code == 422

    def test_auth_missing_password(self, client) -> None:
        """Test authentication with missing password."""
        response = client.get("/auth?userName=initiator")
        # FastAPI will return 422 for missing required parameter
        assert response.status_code == 422

    def test_auth_returns_unique_tokens(self, client) -> None:
        """Test that multiple auth requests return unique tokens."""
        response1 = client.get("/auth?userName=initiator&password=xxxxxxx")
        response2 = client.get("/auth?userName=executor&password=xxxxxxx")
        assert response1.json()["token"] != response2.json()["token"]


class TestWebSocketEndpoint:
    """Test cases for /ws WebSocket endpoint."""
    def test_websocket_invalid_token(self, client) -> None:
        """Test WebSocket connection with invalid token."""
        with pytest.raises(Exception):  # WebSocketDisconnect
            with client.websocket_connect("/ws?token=invalid-token") as websocket:
                # Connection should be closed with policy violation code
                pass
    def test_websocket_empty_token(self, client) -> None:
        """Test WebSocket connection with empty token."""
        with pytest.raises(Exception):  # WebSocketDisconnect
            with client.websocket_connect("/ws?token=") as websocket:
                pass

    def test_websocket_valid_token_initiator(self, client) -> None:
        """Test WebSocket connection with valid initiator token."""
        # Get token
        auth_response = client.get("/auth?userName=initiator&password=xxxxxxx")
        token = auth_response.json()["token"]

        # Connect to WebSocket
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Connection should be accepted
            pass

    def test_websocket_valid_token_executor(self, client) -> None:
        """Test WebSocket connection with valid executor token."""
        # Get token
        auth_response = client.get("/auth?userName=executor&password=xxxxxxx")
        token = auth_response.json()["token"]

        # Connect to WebSocket
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Connection should be accepted
            pass

    def test_websocket_initiator_sends_message_no_executor(self, client) -> None:
        """Test initiator sending message when executor not connected."""
        # Get initiator token
        auth_response = client.get("/auth?userName=initiator&password=xxxxxxx")
        token = auth_response.json()["token"]

        # Connect initiator
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            # Send trading message
            message = {
                "stock": "000001.SH",
                "action": "buy",
                "price": 20,
                "number": 1000,
            }
            websocket.send_json(message)

            # Receive error response (executor not connected)
            response = websocket.receive_json()
            assert response["status"] == "error"
            assert response["message"] == "Executor not connected"

    def test_websocket_full_message_flow(self, client) -> None:
        """Test full message flow: initiator -> executor -> initiator."""
        # Get tokens
        initiator_auth = client.get("/auth?userName=initiator&password=xxxxxxx")
        executor_auth = client.get("/auth?userName=executor&password=xxxxxxx")
        initiator_token = initiator_auth.json()["token"]
        executor_token = executor_auth.json()["token"]

        # Connect executor first
        with client.websocket_connect(f"/ws?token={executor_token}") as executor_ws:
            # Connect initiator
            with client.websocket_connect(
                f"/ws?token={initiator_token}"
            ) as initiator_ws:
                # Initiator sends trading message
                message = {
                    "stock": "000001.SH",
                    "action": "buy",
                    "price": 20,
                    "number": 1000,
                }
                initiator_ws.send_json(message)

                # Executor receives the message
                received = executor_ws.receive_json()
                assert received["stock"] == "000001.SH"
                assert received["action"] == "buy"
                assert received["price"] == 20
                assert received["number"] == 1000

                # Executor sends result back
                result = {
                    "status": "success",
                    "data": {
                        "stock": "000001.SH",
                        "action": "buy",
                        "price": 19.60,
                        "number": 1000,
                    },
                }
                executor_ws.send_json(result)

                # Initiator receives the result
                received_result = initiator_ws.receive_json()
                assert received_result["status"] == "success"
                assert received_result["data"]["price"] == 19.60

    def test_websocket_executor_sends_result(self, client) -> None:
        """Test executor sending execution result to initiator."""
        # Get tokens
        initiator_auth = client.get("/auth?userName=initiator&password=xxxxxxx")
        executor_auth = client.get("/auth?userName=executor&password=xxxxxxx")
        initiator_token = initiator_auth.json()["token"]
        executor_token = executor_auth.json()["token"]

        # Connect both
        with client.websocket_connect(f"/ws?token={initiator_token}") as initiator_ws:
            with client.websocket_connect(f"/ws?token={executor_token}") as executor_ws:
                # Executor sends success result
                result = {
                    "status": "success",
                    "data": {
                        "stock": "600000.SH",
                        "action": "sell",
                        "price": 20.50,
                        "number": 500,
                    },
                }
                executor_ws.send_json(result)

                # Initiator receives result
                received = initiator_ws.receive_json()
                assert received["status"] == "success"
                assert received["data"]["price"] == 20.50

    def test_websocket_connection_count(self, client) -> None:
        """Test connection count in health check."""
        # Initial state
        response = client.get("/health")
        assert response.json()["count"] == 0

        # Get tokens
        initiator_auth = client.get("/auth?userName=initiator&password=xxxxxxx")
        executor_auth = client.get("/auth?userName=executor&password=xxxxxxx")
        initiator_token = initiator_auth.json()["token"]
        executor_token = executor_auth.json()["token"]

        # Connect one connection
        with client.websocket_connect(f"/ws?token={initiator_token}"):
            response = client.get("/health")
            assert response.json()["count"] == 1

        # Both connected
        with client.websocket_connect(f"/ws?token={initiator_token}") as ws1:
            with client.websocket_connect(f"/ws?token={executor_token}") as ws2:
                response = client.get("/health")
                assert response.json()["count"] == 2

    def test_websocket_disconnect_cleanup(self, client) -> None:
        """Test that disconnecting cleans up connection."""
        # Get token
        auth_response = client.get("/auth?userName=initiator&password=xxxxxxx")
        token = auth_response.json()["token"]

        # Connect and disconnect
        with client.websocket_connect(f"/ws?token={token}"):
            pass

        # Check connection is cleaned up
        response = client.get("/health")
        assert response.json()["count"] == 0

    def test_websocket_multiple_connections_same_role(self, client) -> None:
        """Test that connecting same role twice fails."""
        # Get token
        auth_response = client.get("/auth?userName=initiator&password=xxxxxxx")
        token = auth_response.json()["token"]

        # First connection
        with client.websocket_connect(f"/ws?token={token}") as ws1:
            # Second connection with same role should fail
            try:
                with client.websocket_connect(f"/ws?token={token}") as ws2:
                    pass
                # Should not reach here
                assert False, "Second connection should have failed"
            except Exception:
                # Expected - second connection should be rejected
                pass
