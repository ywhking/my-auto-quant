"""Main entry point for trader_initiator module.

Allows running the initiator client as a standalone module to send trading orders:
    python -m trader_initiator --stock 000001.SH --action buy --price 10.5 --number 1000

Or directly:
    python trader_initiator/__main__.py --stock 600000.SH --action sell --price 25.0 --number 500
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from trader_initiator.client import send_order, validate_stock_code
from trader_initiator.config import Config
from trader_initiator.exceptions import OrderFailedError, ValidationError

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="QMT Trading Initiator - Send trading orders to QMT Proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Buy 1000 shares of Ping An Bank at 10.5
  python -m trader_initiator --stock 000001.SH --action buy --price 10.5 --number 1000

  # Sell 500 shares of Shanghai Pudong Development Bank at 25.0
  python -m trader_initiator --stock 600000.SH --action sell --price 25.0 --number 500

  # Use custom config file
  python -m trader_initiator --config /path/to/config.json --stock 000001.SZ --action buy --price 15.0 --number 2000

Stock Code Format:
  - Shanghai stocks: XXXXXX.SH (e.g., 600000.SH, 000001.SH)
  - Shenzhen stocks: XXXXXX.SZ (e.g., 000001.SZ, 300001.SZ)

Actions:
  - buy:  Purchase stocks
  - sell: Sell stocks
        """,
    )

    # Required arguments
    parser.add_argument(
        "--stock",
        "-s",
        type=str,
        required=True,
        help="Stock code with exchange suffix (e.g., '000001.SH', '600000.SH')",
    )

    parser.add_argument(
        "--action",
        "-a",
        type=str,
        choices=["buy", "sell"],
        required=True,
        help="Trading action: 'buy' or 'sell'",
    )

    parser.add_argument(
        "--price",
        "-p",
        type=float,
        required=True,
        help="Order price (must be > 0)",
    )

    parser.add_argument(
        "--number",
        "-n",
        type=int,
        required=True,
        help="Order quantity (must be > 0, typically multiple of 100)",
    )

    # Optional arguments
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration JSON file",
    )

    parser.add_argument(
        "--log-level",
        "-l",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )

    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    return parser


def confirm_order(stock: str, action: str, price: float, number: int) -> bool:
    """Ask user to confirm the order."""
    print("\n" + "=" * 60)
    print("ORDER CONFIRMATION")
    print("=" * 60)
    print(f"Stock:   {stock}")
    print(f"Action:  {action.upper()}")
    print(f"Price:   {price:.2f}")
    print(f"Number:  {number}")
    print(f"Total:   {price * number:.2f}")
    print("=" * 60)

    while True:
        response = input("\nConfirm order? [y/N]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        elif response in ("n", "no", ""):
            return False
        print("Please enter 'y' or 'n'")


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments."""
    # Validate stock code format
    if not validate_stock_code(args.stock):
        print(f"Error: Invalid stock code format: {args.stock}", file=sys.stderr)
        print("Stock code must match pattern: XXXXXX.SH or XXXXXX.SZ", file=sys.stderr)
        print("Examples: 000001.SH (Shanghai), 000001.SZ (Shenzhen)", file=sys.stderr)
        sys.exit(1)

    # Validate price
    if args.price <= 0:
        print(f"Error: Price must be positive: {args.price}", file=sys.stderr)
        sys.exit(1)

    # Validate number
    if args.number <= 0:
        print(f"Error: Number must be positive: {args.number}", file=sys.stderr)
        sys.exit(1)

    # Warn if number is not multiple of 100
    if args.number % 100 != 0:
        print(
            f"Warning: Order quantity {args.number} is not a multiple of 100",
            file=sys.stderr,
        )
        print(
            "Chinese stock markets typically require lot sizes of 100", file=sys.stderr
        )


async def send_order_async(
    stock: str,
    action: str,
    price: float,
    number: int,
    config_path: str | None = None,
) -> dict:
    """Send order asynchronously."""
    # Load configuration
    config = Config()
    if config_path:
        import json

        with open(config_path, encoding="utf-8") as f:
            config._config_data = json.load(f)
        logger.info(f"Configuration loaded from {config_path}")

    # Send the order
    result = await send_order(stock, action, price, number, config)
    return result


def print_result(result: dict) -> None:
    """Print order result in a formatted way."""
    print("\n" + "=" * 60)
    print("ORDER RESULT")
    print("=" * 60)

    status = result.get("status", "unknown")
    order_id = result.get("order_id", "N/A")

    if status == "success":
        print("Status:  SUCCESS")
        print(f"Order ID: {order_id}")
        data = result.get("data", {})
        if data:
            print(f"Details: {data}")
    else:
        print("Status:  FAILED")
        print(f"Order ID: {order_id}")
        message = result.get("message", "Unknown error")
        print(f"Error:   {message}")

    print("=" * 60)


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Validate arguments
    validate_args(args)

    # Show order summary and confirm
    if not args.yes:
        if not confirm_order(args.stock, args.action, args.price, args.number):
            print("\nOrder cancelled by user.")
            return 0

    try:
        # Send the order
        print(
            f"\nSending order: {args.action.upper()} {args.number} {args.stock} @ {args.price:.2f}"
        )
        print("Please wait...\n")

        result = asyncio.run(
            send_order_async(
                args.stock,
                args.action,
                args.price,
                args.number,
                args.config,
            )
        )

        # Print result
        print_result(result)
        return 0

    except ValidationError as e:
        print(f"\nValidation Error: {e}", file=sys.stderr)
        return 1
    except ConnectionError as e:
        print(f"\nConnection Error: {e}", file=sys.stderr)
        print("Please check:", file=sys.stderr)
        print("  1. QMT Proxy is running", file=sys.stderr)
        print("  2. Executor is connected to Proxy", file=sys.stderr)
        print("  3. Network connection is available", file=sys.stderr)
        return 1
    except TimeoutError as e:
        print(f"\nTimeout Error: {e}", file=sys.stderr)
        print("The order may have been sent but response timed out.", file=sys.stderr)
        return 1
    except OrderFailedError as e:
        print(f"\nOrder Failed: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return 130
    except Exception as e:
        print(f"\nUnexpected Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error occurred")
        return 1


if __name__ == "__main__":
    sys.exit(main())
