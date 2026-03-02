"""CLI entry point for trader_executor module.

Provides the main() function and argument parsing for running the executor.
"""

import argparse
import asyncio
import json
import logging
import sys

from trader_executor.config import ExecutorConfig
from trader_executor.exceptions import QMTConnectionError, QMTExecutionError
from trader_executor.idempotency import IdempotencyHandler
from trader_executor.models import ExecutionResult, TradingMessage
from trader_executor.order_channel import OrderChannel
from trader_executor.qmt_client import QMTClientWrapper
from trader_executor.risk_checker import RiskChecker, RiskCheckError

logger = logging.getLogger(__name__)

qmt_client: QMTClientWrapper | None = None
order_channel: OrderChannel | None = None
idempotency: IdempotencyHandler | None = None
risk_checker: RiskChecker | None = None

async def message_handler( message: str ) -> None:
        """Process a single trading message.

        Args:
            message: JSON string from proxy
            websocket: WebSocket connection for response
        """
        try:
            # Parse message
            data = json.loads(message)
            logger.debug(f"Received message: {data}")

            # Validate with Pydantic model
            trading_msg = TradingMessage(**data)

            # Extract order_id for idempotency check
            order_id = data.get("order_id")

            logger.info(
                f"Processing order: order_id={order_id}, stock={trading_msg.stock}, "
                f"action={trading_msg.action}, price={trading_msg.price}, "
                f"number={trading_msg.number}"
            )

            # Check idempotency - return cached result if duplicate
            if order_id:
                is_duplicate, cached_result = await idempotency.check_and_set(
                    order_id
                )
                if is_duplicate:
                    logger.info(
                        f"Duplicate order detected, returning cached result: order_id={order_id}"
                    )
                    if cached_result:
                        await order_channel.send(json.dumps(cached_result))
                        return
                    # If no cached result, continue but don't execute again

            # Run risk checks before execution
            risk_passed, risk_error = risk_checker.check_all(
                stock=trading_msg.stock,
                action=trading_msg.action,
                price=trading_msg.price,
                number=trading_msg.number,
            )

            if not risk_passed:
                logger.warning(f"Risk check failed: {risk_error}")
                result = ExecutionResult(
                    status="error",
                    order_id=order_id,
                    message=f"Risk check failed: {risk_error}",
                )
                await order_channel.send(result.model_dump_json())
                return

            # Execute order
            order_id_value = await qmt_client.place_order(
                trading_msg.stock,
                trading_msg.action,
                trading_msg.price,
                trading_msg.number,
            )

            # Build response data
            response_data = {
                "stock": trading_msg.stock,
                "action": trading_msg.action,
                "price": trading_msg.price,
                "number": trading_msg.number,
            }
            result = ExecutionResult(
                status="success",
                order_id=str(order_id_value),
                data=response_data,
            )

            # Cache result for idempotency
            if order_id:
                await idempotency.set_result(order_id, result.model_dump())

            await order_channel.send(result.model_dump_json())
            logger.info(f"Order executed successfully: order_id={order_id_value}")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON message: {e}"
            logger.error(error_msg)
            result = ExecutionResult(
                status="error",
                order_id=None,
                message=error_msg,
            )
            await order_channel.send(result.model_dump_json())

        except ValueError as e:
            # Pydantic validation error
            error_msg = f"Validation error: {e}"
            logger.error(error_msg)
            result = ExecutionResult(
                status="error",
                order_id=None,
                message=error_msg,
            )
            await order_channel.send(result.model_dump_json())

        except RiskCheckError as e:
            error_msg = f"Risk check error: {e}"
            logger.warning(error_msg)
            result = ExecutionResult(
                status="error",
                order_id=None,
                message=error_msg,
            )
            await order_channel.send(result.model_dump_json())

        except (QMTExecutionError, QMTConnectionError) as e:
            error_msg = f"QMT error: {e}"
            logger.error(error_msg)
            result = ExecutionResult(
                status="error",
                order_id=None,
                message=error_msg,
            )
            await order_channel.send(result.model_dump_json())

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg, exc_info=True)
            result = ExecutionResult(
                status="error",
                order_id=None,
                message=error_msg,
            )
            await order_channel.send(result.model_dump_json())


async def run_executor(config_path: str | None = None) -> None:
    """Run the executor client.

    Args:
        config_path: Optional path to configuration JSON file
    """
    global risk_checker
    global idempotency
    global qmt_client
    global order_channel

    try:
        # Load configuration
        config = ExecutorConfig()

        risk_checker = RiskChecker(config)
        idempotency = IdempotencyHandler(ttl=86400)

        # create QMT client and connect
        qmt_client = QMTClientWrapper(config)
        await qmt_client.connect()

        # create order channel and run (connects and runs message loop)
        order_channel = OrderChannel(config, msg_handler=message_handler)
        await order_channel.run()

    except Exception as e:
        logger.error(f"Error running executor: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="QMT Trading Executor - Connects to QMT Proxy and executes orders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m trader_executor
  python -m trader_executor --config /path/to/config.json
  python -m trader_executor --help
        """,
    )

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

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s",
    )

    try:
        asyncio.run(run_executor(args.config))
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        sys.exit(0)
