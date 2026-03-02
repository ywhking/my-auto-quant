"""Tests for callback handler in trader_executor."""

from unittest.mock import MagicMock

from trader_executor.callback import ExecutorCallback


class TestExecutorCallback:
    """Test cases for ExecutorCallback class."""

    def test_callback_initialization(self) -> None:
        """Test callback initialization."""
        callback = ExecutorCallback()
        assert callback.get_all_results() == {}

    def test_on_disconnected(self) -> None:
        """Test on_disconnected callback."""
        callback = ExecutorCallback()
        # Just ensure it doesn't raise an exception
        callback.on_disconnected()

    def test_on_order_stock_success(self, mock_order: MagicMock) -> None:
        """Test on_order_stock callback with successful order."""
        callback = ExecutorCallback()
        callback.on_order_stock(mock_order)

        result = callback.get_result("123456")
        assert result is not None
        assert result.order_id == "123456"
        assert result.order_status == 53
        assert result.status_msg == "Order executed"

    def test_on_order_stock_with_missing_order_id(self, mock_order: MagicMock) -> None:
        """Test on_order_stock callback with missing order_id."""
        callback = ExecutorCallback()
        mock_order.order_id = None

        callback.on_order_stock(mock_order)

        # Should not store result without order_id
        result = callback.get_result(None)
        assert result is None

    def test_on_trade_stock(self, mock_trade: MagicMock) -> None:
        """Test on_trade_stock callback."""
        callback = ExecutorCallback()
        callback.on_trade_stock(mock_trade)

        result = callback.get_result("123456")
        assert result is not None
        assert result.order_id == "123456"
        assert result.traded_volume == 1000
        assert result.traded_price == 19.60

    def test_on_trade_stock_updates_existing_result(
        self, mock_order: MagicMock, mock_trade: MagicMock
    ) -> None:
        """Test on_trade_stock updates existing order result."""
        callback = ExecutorCallback()

        # First call on_order_stock
        callback.on_order_stock(mock_order)

        # Then call on_trade_stock
        callback.on_trade_stock(mock_trade)

        result = callback.get_result("123456")
        assert result is not None
        assert result.order_id == "123456"
        assert result.order_status == 53  # From order callback
        assert result.status_msg == "Order executed"  # From order callback
        assert result.traded_volume == 1000  # From trade callback
        assert result.traded_price == 19.60  # From trade callback

    def test_on_order_error(self, mock_order_error: MagicMock) -> None:
        """Test on_order_error callback."""
        callback = ExecutorCallback()
        callback.on_order_error(mock_order_error)

        result = callback.get_result("123456")
        assert result is not None
        assert result.order_id == "123456"
        assert result.status_msg == "Insufficient funds"

    def test_on_order_error_with_missing_order_id(
        self, mock_order_error: MagicMock
    ) -> None:
        """Test on_order_error callback with missing order_id."""
        callback = ExecutorCallback()
        mock_order_error.order_id = None

        callback.on_order_error(mock_order_error)

        # Should not store result without order_id
        result = callback.get_result(None)
        assert result is None

    def test_get_result_not_found(self) -> None:
        """Test getting result for non-existent order."""
        callback = ExecutorCallback()
        result = callback.get_result("999999")
        assert result is None

    def test_clear_result(self, mock_order: MagicMock) -> None:
        """Test clearing a specific result."""
        callback = ExecutorCallback()
        callback.on_order_stock(mock_order)

        # Verify result exists
        assert callback.get_result("123456") is not None

        # Clear the result
        callback.clear_result("123456")

        # Verify result is cleared
        assert callback.get_result("123456") is None

    def test_clear_all_results(self, mock_order: MagicMock) -> None:
        """Test clearing all results."""
        callback = ExecutorCallback()

        # Add multiple results
        mock_order.order_id = "123456"
        callback.on_order_stock(mock_order)

        mock_order.order_id = "234567"
        callback.on_order_stock(mock_order)

        # Verify results exist
        assert len(callback.get_all_results()) == 2

        # Clear all results
        callback.clear_all_results()

        # Verify all results are cleared
        assert len(callback.get_all_results()) == 0

    def test_get_all_results(self, mock_order: MagicMock) -> None:
        """Test getting all results."""
        callback = ExecutorCallback()

        # Add multiple results
        mock_order.order_id = "123456"
        callback.on_order_stock(mock_order)

        mock_order.order_id = "234567"
        callback.on_order_stock(mock_order)

        # Get all results
        results = callback.get_all_results()
        assert len(results) == 2
        assert "123456" in results
        assert "234567" in results

    def test_get_all_results_returns_copy(self, mock_order: MagicMock) -> None:
        """Test that get_all_results returns a copy, not reference."""
        callback = ExecutorCallback()
        callback.on_order_stock(mock_order)

        results1 = callback.get_all_results()
        results2 = callback.get_all_results()

        # Should be different objects (copies)
        assert results1 is not results2

        # But same content
        assert results1 == results2

    def test_order_status_codes(self, mock_order: MagicMock) -> None:
        """Test different order status codes."""
        callback = ExecutorCallback()

        status_codes = [
            (50, "已报"),
            (51, "待撤"),
            (52, "部成"),
            (53, "全成"),
            (54, "已撤"),
            (55, "部撤"),
            (56, "废单"),
        ]

        for status_code, status_desc in status_codes:
            mock_order.order_id = f"order_{status_code}"
            mock_order.order_status = status_code
            mock_order.status_msg = status_desc

            callback.on_order_stock(mock_order)

            result = callback.get_result(f"order_{status_code}")
            assert result is not None
            assert result.order_status == status_code
            assert result.status_msg == status_desc

    def test_multiple_order_ids(self, mock_order: MagicMock) -> None:
        """Test handling multiple order IDs."""
        callback = ExecutorCallback()

        order_ids = ["100001", "100002", "100003"]

        for order_id in order_ids:
            mock_order.order_id = order_id
            callback.on_order_stock(mock_order)

        # Verify all results are stored
        for order_id in order_ids:
            result = callback.get_result(order_id)
            assert result is not None
            assert result.order_id == order_id

    def test_thread_safety(self, mock_order: MagicMock) -> None:
        """Test that callback is thread-safe (basic check)."""
        import threading

        callback = ExecutorCallback()
        errors = []

        def store_order(order_id: str) -> None:
            try:
                mock_order.order_id = order_id
                callback.on_order_stock(mock_order)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = [
            threading.Thread(target=store_order, args=(f"order_{i}",))
            for i in range(10)
        ]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Check for errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all results are stored
        for i in range(10):
            result = callback.get_result(f"order_{i}")
            assert result is not None
