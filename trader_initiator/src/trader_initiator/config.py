"""Configuration management for trader_initiator module."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
config_path = Path(__file__).parent.parent.parent / "config" / "config.json"


class Config:
    """Configuration manager for trader_initiator.

    Loads configuration from config/initiator.json and provides
    convenient access to configuration values.
    """

    _instance: "Config | None" = None
    _config_data: dict[str, Any] = {}

    def __new__(cls) -> "Config":
        """Singleton pattern to ensure only one Config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize configuration by loading from JSON file."""
        if not Config._config_data:
            self._load_config()

    def _load_config(self) -> None:
        """Load configuration from config.json."""
        if not config_path.exists():
            # Use default configuration if file doesn't exist
            logger.warning(f"Config file not found at {config_path}, using defaults")
            raise FileNotFoundError(f"Config file not found at {config_path}")
        else:
            try:
                with open(config_path, encoding="utf-8") as f:
                    Config._config_data = json.load(f)
                logger.info(f"Configuration loaded from {config_path}")
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load config file: {e}, using defaults")
                raise

    @property
    def proxy_host(self) -> str:
        """Get proxy host."""
        return self._config_data.get("proxy", {}).get("host", "localhost")

    @property
    def proxy_port(self) -> int:
        """Get proxy port."""
        return self._config_data.get("proxy", {}).get("port", 8000)

    @property
    def ws_path(self) -> str:
        """Get WebSocket path."""
        return self._config_data.get("proxy", {}).get("ws_path", "/ws")

    @property
    def token_path(self) -> str:
        """Get token endpoint path."""
        return self._config_data.get("proxy", {}).get("token_path", "/auth")

    @property
    def username(self) -> str:
        """Get authentication username."""
        return self._config_data.get("auth", {}).get("username", "initiator")

    @property
    def password(self) -> str:
        """Get authentication password."""
        return self._config_data.get("auth", {}).get("password", "xxxxxxx")

    @property
    def timeout(self) -> int:
        """Get request timeout in seconds."""
        return self._config_data.get("timeout", 30)

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config_data.get("logging", {}).get("level", "INFO")

    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self._config_data.get("logging", {}).get("file", "logs/initiator.log")

    @property
    def use_https(self) -> bool:
        """Get whether to use HTTPS/WSS."""
        return self._config_data.get("use_https", False)

    @property
    def verify_ssl(self) -> bool:
        """Get whether to verify SSL certificates."""
        return self._config_data.get("verify_ssl", True)
    @property
    def proxy_url(self) -> str:
        """Get proxy base URL (e.g., 'http://localhost:8000' or 'https://localhost:8000')."""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.proxy_host}:{self.proxy_port}"

    @property
    def token_url(self) -> str:
        """Get token endpoint URL."""
        return f"{self.proxy_url}{self.token_path}"

    @property
    def ws_url(self) -> str:
        """Get WebSocket base URL (e.g., 'ws://localhost:8000' or 'wss://localhost:8000')."""
        protocol = "wss" if self.use_https else "ws"
        return f"{protocol}://{self.proxy_host}:{self.proxy_port}"

    def reload(self) -> None:
        """Reload configuration from file."""
        Config._config_data = {}
        self._load_config()
        logger.info("Configuration reloaded")
