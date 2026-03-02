"""Configuration management for trader_executor module."""

import json
import logging
import ssl
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
config_path = Path(__file__).parent.parent.parent / "config" / "config.json"

class ExecutorConfig:
    """Configuration manager for trader_executor.

    Loads configuration from config.json and provides convenient access
    to configuration values using a singleton pattern.

    Configuration sections:
    - proxy: Proxy server connection settings
    - auth: Authentication credentials
    - qmt: QMT client settings
    - connection: Connection management (reconnect, heartbeat)
    - trading: Trading rules (lot size, tick size, hours)
    - logging: Logging configuration
    """

    _instance: "ExecutorConfig | None" = None
    _config_data: dict[str, Any] = {}

    def __new__(cls) -> "ExecutorConfig":
        """Singleton pattern to ensure only one Config instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize configuration by loading from JSON file."""
        if not ExecutorConfig._config_data:
            self._load_config()

    def _load_config(self) -> None:
        """Load configuration from config.json.
        
        Looks for config.json in the following locations (in order):
        1. Project root config/ directory
        2. Same directory as this file (for backward compatibility)
        """

        if not config_path.exists():
            # 配置文件不存在，退出程序
            logger.error(f"Config file not found at {config_path}, exiting program")
            raise FileNotFoundError(f"Config file not found at {config_path}")
        else:
            try:
                with open(config_path, encoding="utf-8") as f:
                    ExecutorConfig._config_data = json.load(f)
                logger.info(f"Configuration loaded from {config_path}")
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Failed to load config file: {e}, exiting program")
                raise RuntimeError(f"Failed to load config file: {e}")
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
        return self._config_data.get("proxy", {}).get("token_path", "/token")

    @property
    def username(self) -> str:
        """Get authentication username."""
        return self._config_data.get("auth", {}).get("username", "executor")

    @property
    def password(self) -> str:
        """Get authentication password."""
        return self._config_data.get("auth", {}).get("password", "xxxxxxx")

    @property
    def qmt_account_id(self) -> str:
        """Get QMT account ID."""
        return self._config_data.get("qmt", {}).get("account_id", "8885385377")

    @property
    def qmt_password(self) -> str:
        """Get QMT password."""
        return self._config_data.get("qmt", {}).get("password", "your_qmt_password")

    @property
    def qmt_min_path(self) -> str:
        """Get QMT min path."""
        return self._config_data.get("qmt", {}).get(
            "min_path", r"D:\国金证券QMT交易端\userdata_mini"
        )

    @property
    def heartbeat_interval(self) -> int:
        """Get heartbeat interval in seconds."""
        return self._config_data.get("connection", {}).get("heartbeat_interval", 30)

    @property
    def max_reconnect_attempts(self) -> int:
        """Get maximum reconnect attempts."""
        return self._config_data.get("connection", {}).get("max_reconnect_attempts", 10)

    @property
    def reconnect_backoff_base(self) -> int:
        """Get reconnect backoff base multiplier."""
        return self._config_data.get("connection", {}).get("reconnect_backoff_base", 2)

    @property
    def initial_reconnect_delay(self) -> int:
        """Get initial reconnect delay in seconds."""
        return self._config_data.get("connection", {}).get("initial_reconnect_delay", 1)

    @property
    def max_reconnect_delay(self) -> int:
        """Get maximum reconnect delay in seconds."""
        return self._config_data.get("connection", {}).get("max_reconnect_delay", 60)

    @property
    def lot_size(self) -> int:
        """Get trading lot size."""
        return self._config_data.get("trading", {}).get("lot_size", 100)

    @property
    def min_tick(self) -> float:
        """Get minimum tick size."""
        return self._config_data.get("trading", {}).get("min_tick", 0.01)

    @property
    def market_open(self) -> str:
        """Get market open time."""
        return self._config_data.get("trading", {}).get("market_open", "09:30:00")

    @property
    def market_close(self) -> str:
        """Get market close time."""
        return self._config_data.get("trading", {}).get("market_close", "15:00:00")

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config_data.get("logging", {}).get("level", "INFO")

    @property
    def allow_mock(self) -> bool:
        """Get allow mock mode for testing."""
        return self._config_data.get("allow_mock", False)

    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self._config_data.get("logging", {}).get("file", "logs/executor.log")

    @property
    def use_ssl(self) -> bool:
        """Get whether to use SSL/TLS for connections."""
        return self._config_data.get("proxy", {}).get("use_ssl", False)

    @property
    def ssl_verify(self) -> bool:
        """Get whether to verify SSL certificates."""
        return self._config_data.get("proxy", {}).get("ssl_verify", True)

    @property
    def ssl_cert_path(self) -> str | None:
        """Get path to SSL client certificate file."""
        return self._config_data.get("proxy", {}).get("ssl_cert_path")

    @property
    def ssl_key_path(self) -> str | None:
        """Get path to SSL client key file."""
        return self._config_data.get("proxy", {}).get("ssl_key_path")

    @property
    def ssl_ca_path(self) -> str | None:
        """Get path to SSL CA certificate file for custom CA."""
        return self._config_data.get("proxy", {}).get("ssl_ca_path")

    @property
    def proxy_url(self) -> str:
        """Get proxy base URL (e.g., 'http://localhost:8000' or 'https://localhost:8000')."""
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.proxy_host}:{self.proxy_port}"

    @property
    def token_url(self) -> str:
        """Get token endpoint URL."""
        return f"{self.proxy_url}{self.token_path}"

    @property
    def ws_url(self) -> str:
        """Get WebSocket base URL (e.g., 'ws://localhost:8000' or 'wss://localhost:8000')."""
        scheme = "wss" if self.use_ssl else "ws"
        return f"{scheme}://{self.proxy_host}:{self.proxy_port}"

    def get_ssl_context(self) -> ssl.SSLContext | None:
        """Create and return SSL context for secure connections.

        Returns:
            SSLContext configured for client connections, or None if SSL is disabled.
        """
        if not self.use_ssl:
            return None

        # Create default client SSL context
        if self.ssl_ca_path:
            # Use custom CA certificate
            ssl_context = ssl.create_default_context(cafile=self.ssl_ca_path)
        elif not self.ssl_verify:
            # Disable certificate verification (not recommended for production)
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        else:
            # Use system default CA certificates
            ssl_context = ssl.create_default_context()

        # Load client certificate if provided
        if self.ssl_cert_path and self.ssl_key_path:
            ssl_context.load_cert_chain(
                certfile=self.ssl_cert_path,
                keyfile=self.ssl_key_path,
            )
        elif self.ssl_cert_path:
            ssl_context.load_cert_chain(certfile=self.ssl_cert_path)

        return ssl_context

    def reload(self) -> None:
        """Reload configuration from file."""
        ExecutorConfig._config_data = {}
        self._load_config()
        logger.info("Configuration reloaded")
