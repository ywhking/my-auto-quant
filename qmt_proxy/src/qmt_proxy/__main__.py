"""Entry point for running QMT Proxy as a module.

Usage:
    python -m qmt_proxy
    python -m qmt_proxy --host 0.0.0.0 --port 8000
"""

import argparse
import uvicorn

from .main import app


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="QMT Proxy - Trading message relay server",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Logging level (default: info)",
    )
    args = parser.parse_args()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
