"""Main FastAPI application for QMT Proxy.

Provides REST and WebSocket endpoints for token authentication
and trading message forwarding.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from .auth import authenticate_user, clear_all_tokens, validate_token
from .connection_manager import ConnectionManager
from .exceptions import AuthenticationError, InvalidTokenError
from .models import (
    ErrorResponse,
    ExecutorNotConnectedResponse,
    TokenResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Connection manager instance
connection_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("QMT Proxy starting up...")

    yield

    # Shutdown - runs automatically when server receives SIGINT/SIGTERM
    logger.info("QMT Proxy shutting down...")
    # Close all WebSocket connections
    await connection_manager.close_all_connections()
    logger.info("All connections closed")

# Create FastAPI application
app = FastAPI(
    title="QMT Proxy",
    description="Trading message relay between Trading Initiator and Trading Executor",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/auth", response_model=TokenResponse)
async def get_auth_token(userName: str, password: str):
    """Get authentication token for WebSocket connection.

    Args:
        userName: Username (e.g., 'initiator' or 'executor')
        password: User password

    Returns:
        TokenResponse: Contains authentication token

    Raises:
        HTTPException: 401 if authentication fails
    """
    try:
        token = authenticate_user(userName, password)
        logger.info(f"Token issued to user: {userName}")
        return TokenResponse(token=token)
    except AuthenticationError as e:
        logger.warning(f"Authentication failed for user: {userName}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid credentials"},
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for trading message forwarding.

    Connection role is determined by the authenticated user.

    Args:
        websocket: WebSocket connection
        token: Authentication token from query parameter
    """
    # Validate token and get user role
    try:
        username, role = validate_token(token)
    except InvalidTokenError:
        logger.warning("WebSocket connection rejected: invalid token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept connection
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for role: {role}, user: {username}")

    # Add connection to manager
    try:
        await connection_manager.connect(role, websocket)
    except Exception as e:
        logger.error(f"Failed to add connection for role {role}: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    try:
        # Message loop
        while True:
            # Receive message
            data = await websocket.receive_json()
            logger.info(f"Message received from {role}: {data}")

            # Handle message based on sender role
            if role == "initiator":
                # Initiator -> Proxy -> Executor
                try:
                    await connection_manager.send_to_executor(data)
                except Exception as e:
                    logger.error(f"Failed to forward message to executor: {e}")
                    # Send error response back to initiator
                    error_response = ExecutorNotConnectedResponse().model_dump()
                    await connection_manager.send_to_initiator(error_response)

            elif role == "executor":
                # Executor -> Proxy -> Initiator
                try:
                    await connection_manager.send_to_initiator(data)
                except Exception as e:
                    logger.error(f"Failed to forward message to initiator: {e}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for role: {role}")
    except Exception as e:
        logger.error(f"WebSocket error for role {role}: {e}")
    finally:
        # Remove connection from manager
        await connection_manager.disconnect(role)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    connections = connection_manager.get_connected_roles()
    return {
        "status": "healthy",
        "connections": connections,
        "count": connection_manager.get_connection_count(),
    }


# For testing purposes
@app.post("/test/reset")
async def test_reset():
    """Reset all tokens and connections (testing only)."""
    clear_all_tokens()
    ConnectionManager.clear_all_connections()
    logger.warning("All tokens and connections cleared (test reset)")
    return {"status": "reset"}
