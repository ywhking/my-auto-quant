"""Tests for QMT client wrapper in trader_executor."""

from unittest.mock import MagicMock, patch

import pytest

from trader_executor.config import ExecutorConfig
from trader_executor.exceptions import QMTConnectionError, QMTExecutionError
from trader_executor.qmt_client import QMTClientWrapper


class TestQMTClientWrapper:
    """Test cases for QMTClientWrapper class."""

    def test_initialization(self) -> None:
        """Test client initialization."""
        client = QMTClientWrapper()
        assert client.config is not None
        assert isinstance(client.config, ExecutorConfig)
        assert not client.is_connected
        assert not client.is_subscribed

    def test_initialization_with_config(self) -> None:
        """Test client initialization with custom config."""
        config = ExecutorConfig()
        client = QMTClientWrapper(config)
        assert client.config is config

    @pytest.mark.asyncio
    async def test_connect_without_xtquant(self) -> None:
        """Test connection when xtquant is not available (mock mode)."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", False):
            config = ExecutorConfig()
            config._config_data["allow_mock"] = True
            client = QMTClientWrapper(config)
            await client.connect()

            assert client.is_connected
            assert client.is_subscribed
            await client.connect()

            assert client.is_connected
            assert client.is_subscribed

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful connection to QMT."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()

            # Mock XtQuantTrader and StockAccount
            mock_xt_trader = MagicMock()
            mock_xt_trader.connect.return_value = 0
            mock_xt_trader.subscribe.return_value = 0

            mock_stock_account = MagicMock()

            with patch(
                "trader_executor.qmt_client.XtQuantTrader", return_value=mock_xt_trader
            ):
                with patch(
                    "trader_executor.qmt_client.StockAccount",
                    return_value=mock_stock_account,
                ):
                    await client.connect()

                    assert client.is_connected
                    assert client.is_subscribed
                    assert mock_xt_trader.register_callback.called
                    assert mock_xt_trader.start.called
                    assert mock_xt_trader.connect.called

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        """Test connection failure to QMT."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()

            # Mock XtQuantTrader to return error
            mock_xt_trader = MagicMock()
            mock_xt_trader.connect.return_value = -1  # Error code

            mock_stock_account = MagicMock()

            with patch(
                "trader_executor.qmt_client.XtQuantTrader", return_value=mock_xt_trader
            ):
                with patch(
                    "trader_executor.qmt_client.StockAccount",
                    return_value=mock_stock_account,
                ):
                    with pytest.raises(QMTConnectionError) as exc_info:
                        await client.connect()

                    assert "connection failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_connect_subscribe_failure(self) -> None:
        """Test subscribe failure after successful connect."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()

            # Mock XtQuantTrader
            mock_xt_trader = MagicMock()
            mock_xt_trader.connect.return_value = 0
            mock_xt_trader.subscribe.return_value = -1  # Error code

            mock_stock_account = MagicMock()

            with patch(
                "trader_executor.qmt_client.XtQuantTrader", return_value=mock_xt_trader
            ):
                with patch(
                    "trader_executor.qmt_client.StockAccount",
                    return_value=mock_stock_account,
                ):
                    with pytest.raises(QMTConnectionError) as exc_info:
                        await client.connect()

                    assert "subscription failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_place_order_buy(self) -> None:
        """Test placing a buy order."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()
            client._connected = True
            client._account = MagicMock()

            # Mock xtquant order_stock
            mock_xt_trader = MagicMock()
            mock_xt_trader.order_stock.return_value = 123456
            client._xt_trader = mock_xt_trader

            with patch("trader_executor.qmt_client.xtconstant") as mock_constant:
                mock_constant.STOCK_BUY = 49
                mock_constant.STOCK_SELL = 50
                mock_constant.FIX_PRICE = 1

                order_id = await client.place_order("000001.SH", "buy", 19.60, 1000)

                assert order_id == 123456
                mock_xt_trader.order_stock.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_order_sell(self) -> None:
        """Test placing a sell order."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()
            client._connected = True
            client._account = MagicMock()

            # Mock xtquant order_stock
            mock_xt_trader = MagicMock()
            mock_xt_trader.order_stock.return_value = 234567
            client._xt_trader = mock_xt_trader

            with patch("trader_executor.qmt_client.xtconstant") as mock_constant:
                mock_constant.STOCK_BUY = 49
                mock_constant.STOCK_SELL = 50
                mock_constant.FIX_PRICE = 1

                order_id = await client.place_order("000001.SH", "sell", 19.60, 1000)

                assert order_id == 234567
                mock_xt_trader.order_stock.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_order_not_connected(self) -> None:
        """Test placing order when not connected."""
        client = QMTClientWrapper()
        client._connected = False

        with pytest.raises(QMTConnectionError):
            await client.place_order("000001.SH", "buy", 19.60, 1000)

    @pytest.mark.asyncio
    async def test_place_order_invalid_action(self) -> None:
        """Test placing order with invalid action."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()
            client._connected = True
            client._account = MagicMock()
            client._xt_trader = MagicMock()

            with pytest.raises(QMTExecutionError):
                await client.place_order("000001.SH", "invalid", 19.60, 1000)

    @pytest.mark.asyncio
    async def test_place_order_failure(self) -> None:
        """Test order placement failure."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()
            client._connected = True
            client._account = MagicMock()

            # Mock xtquant order_stock to return error
            mock_xt_trader = MagicMock()
            mock_xt_trader.order_stock.return_value = -1  # Error
            client._xt_trader = mock_xt_trader

            with patch("trader_executor.qmt_client.xtconstant") as mock_constant:
                mock_constant.STOCK_BUY = 49
                mock_constant.FIX_PRICE = 1

                with pytest.raises(QMTExecutionError):
                    await client.place_order("000001.SH", "buy", 19.60, 1000)

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnection from QMT."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", True):
            client = QMTClientWrapper()
            client._connected = True
            client._subscribed = True

            mock_xt_trader = MagicMock()
            client._xt_trader = mock_xt_trader

            await client.disconnect()

            assert not client.is_connected
            assert not client.is_subscribed
            assert client._xt_trader is None
            assert client._account is None

    @pytest.mark.asyncio
    async def test_disconnect_without_xtquant(self) -> None:
        """Test disconnection when xtquant is not available (mock mode)."""
        with patch("trader_executor.qmt_client.XTQUANT_AVAILABLE", False):
            config = ExecutorConfig()
            config._config_data["allow_mock"] = True
            client = QMTClientWrapper(config)
            client._connected = True
            client._subscribed = True

            await client.disconnect()

            assert not client.is_connected
            assert not client.is_subscribed
            client._connected = True
            client._subscribed = True

            await client.disconnect()

            assert not client.is_connected
            assert not client.is_subscribed

    def test_callback_property(self) -> None:
        """Test callback property."""
        client = QMTClientWrapper()
        assert client.callback is None

        mock_callback = MagicMock()
        client._callback = mock_callback
        assert client.callback is mock_callback

    def test_xt_trader_property(self) -> None:
        """Test xt_trader property."""
        client = QMTClientWrapper()
        assert client.xt_trader is None

        mock_trader = MagicMock()
        client._xt_trader = mock_trader
        assert client.xt_trader is mock_trader
