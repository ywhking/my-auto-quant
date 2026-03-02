"""Main WebSocket client for trader_executor.

This module provides the channel between the executor and QMT Proxy via
WebSocket, receives trading messages, and sends execution results.
"""

import json
import logging
from typing import Any

import aiohttp
import websockets

from trader_executor.config import ExecutorConfig

logger = logging.getLogger(__name__)

class OrderChannel:
    def __init__(self, config: ExecutorConfig, msg_handler: Any) -> None:
        """Initialize ExecutorClient.

        Args:
            config: Configuration object
            msg_handler: Message handler callback
        """
        self.token_url = config.token_url
        logger.info(f"Token URL set to: {self.token_url}")
        self.username = config.username
        logger.info(f"Username set to: {self.username}")
        self.password = config.password
        logger.info(f"Password set to: {self.password}")
        self.use_ssl = config.use_ssl
        logger.info(f"SSL usage set to: {self.use_ssl}")
        self.ws_url = config.ws_url
        logger.info(f"WebSocket URL set to: {self.ws_url}")
        self.ws_path = config.ws_path
        logger.info(f"WebSocket path set to: {self.ws_path}")
        self.heartbeat_interval = config.heartbeat_interval
        logger.info(f"Heartbeat interval set to: {self.heartbeat_interval}")

        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.msg_handler = msg_handler

    async def run(self) -> None:
        """Connect to WebSocket and run message loop.

        This method establishes the WebSocket connection and runs the
        message receive loop. The connection stays open until it's closed
        or an error occurs.
        """
        try:
            token = await self._get_token()
            ws_url = (
                f"{self.ws_url}{self.ws_path}?token={token}&role=executor"
            )

            logger.info(f"Connecting to WebSocket: {ws_url}")

            async with websockets.connect(
                ws_url,
                close_timeout=self.heartbeat_interval,
                ping_interval=self.heartbeat_interval,
                # ssl=self.use_ssl,
            ) as websocket:
                self.websocket = websocket
                logger.info("WebSocket connected")

                # Run message receive loop
                logger.info("Starting message receive loop...")
                async for message in websocket:
                    logger.debug(f"Received message: {message}")
                    if self.msg_handler:
                        await self.msg_handler(message)

        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in WebSocket loop: {e}", exc_info=True)
            raise

    async def _get_token(self) -> str:
        """Get authentication token from QMT Proxy.

        Returns:
            Authentication token string

        Raises:
            ConnectionError: If token request fails
        """
        url = f"{self.token_url}?userName={self.username}&password={self.password}"
        logger.info(f"Requesting token from URL: {url}")
        try:
            # Create aiohttp connector with SSL context
            connector = aiohttp.TCPConnector(ssl=self.use_ssl)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        token = data["token"]
                        logger.info("Token obtained successfully")
                        return token
                    error_msg = f"Authentication failed: HTTP {response.status}"
                    logger.error(error_msg)
                    raise ConnectionError(error_msg)
        except (aiohttp.ClientError, json.JSONDecodeError, ConnectionError) as e:
            error_msg = f"Failed to get token: {e}"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e


    async def send(self, message: str) -> None:
        """Send messages to WebSocket.

        Args:
            message: Message to send

        Note:
            This method must be called while the connection is active
            (inside the message handler during run()).
        """
        if self.websocket is None:
            logger.error("WebSocket is not connected")
            raise ConnectionError("WebSocket is not connected")

        try:
            await self.websocket.send(message)
            logger.debug(f"Sent message: {message}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}", exc_info=True)
            raise




    async def close(self) -> None:
        """Close WebSocket connection."""
        logger.info("Close websocket ...")
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")
            self.websocket = None
