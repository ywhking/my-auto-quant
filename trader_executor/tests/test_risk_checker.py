"""Tests for RiskChecker."""


import pytest

from trader_executor.risk_checker import RiskChecker, RiskCheckError


@pytest.fixture
def risk_checker():
    """Create a RiskChecker instance."""
    return RiskChecker()


class TestOrderSize:
    """Test order size validation."""

    def test_valid_order_size(self, risk_checker):
        """Test valid order size."""
        assert risk_checker.check_order_size(100) is True
        assert risk_checker.check_order_size(1000) is True

    def test_order_size_too_small(self, risk_checker):
        """Test order size below minimum."""
        with pytest.raises(RiskCheckError, match="too small"):
            risk_checker.check_order_size(50)

    def test_order_size_too_large(self, risk_checker):
        """Test order size above maximum."""
        with pytest.raises(RiskCheckError, match="too large"):
            risk_checker.check_order_size(200000)

    def test_order_size_not_multiple_of_lot(self, risk_checker):
        """Test order size not multiple of lot size."""
        with pytest.raises(RiskCheckError, match="multiple"):
            risk_checker.check_order_size(150)


class TestOrderAmount:
    """Test order amount validation."""

    def test_valid_order_amount(self, risk_checker):
        """Test valid order amount."""
        assert risk_checker.check_order_amount(10.0, 1000) is True  # 10000

    def test_order_amount_exceeds_limit(self, risk_checker):
        """Test order amount above maximum."""
        with pytest.raises(RiskCheckError, match="exceeds limit"):
            risk_checker.check_order_amount(100.0, 10000)  # 1000000 > 50000


class TestPositionLimit:
    """Test position limit validation."""

    def test_buy_within_limit(self, risk_checker):
        """Test buy order within position limit."""
        assert risk_checker.check_position_limit(
            "000001.SH", "buy", 10.0, 1000, 0, 100000.0
        ) is True  # 10000/100000 = 10%

    def test_buy_exceeds_limit(self, risk_checker):
        """Test buy order exceeding position limit."""
        with pytest.raises(RiskCheckError, match="Position limit exceeded"):
            risk_checker.check_position_limit(
                "000001.SH", "buy", 10.0, 10000, 0, 100000.0
            )  # 100000/100000 = 100% > 50%

    def test_sell_skips_position_check(self, risk_checker):
        """Test sell order skips position check."""
        assert risk_checker.check_position_limit(
            "000001.SH", "sell", 10.0, 1000, 5000, 100000.0
        ) is True


class TestPriceLimit:
    """Test price limit validation."""

    def test_price_within_limit(self, risk_checker):
        """Test price within normal range."""
        assert risk_checker.check_price_limit("000001.SH", 10.5, 10.0) is True

    def test_price_limit_up(self, risk_checker):
        """Test price at limit up."""
        with pytest.raises(RiskCheckError, match="limit up"):
            risk_checker.check_price_limit("000001.SH", 11.0, 10.0)  # 10% up

    def test_price_limit_down(self, risk_checker):
        """Test price at limit down."""
        with pytest.raises(RiskCheckError, match="limit down"):
            risk_checker.check_price_limit("000001.SH", 9.0, 10.0)  # 10% down

    def test_invalid_prev_close(self, risk_checker):
        """Test with invalid previous close price."""
        assert risk_checker.check_price_limit("000001.SH", 10.0, 0) is True
