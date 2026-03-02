"""Tests for IdempotencyHandler."""

import asyncio

import pytest

from trader_executor.idempotency import IdempotencyHandler


@pytest.fixture
def idempotency():
    """Create an IdempotencyHandler with short TTL for testing."""
    return IdempotencyHandler(ttl=2)  # 2 seconds TTL for fast tests


@pytest.mark.asyncio
async def test_new_order(idempotency):
    """Test processing a new order."""
    is_duplicate, cached = await idempotency.check_and_set("order_1")
    assert is_duplicate is False
    assert cached is None


@pytest.mark.asyncio
async def test_duplicate_order(idempotency):
    """Test detecting a duplicate order."""
    # First request
    is_duplicate, cached = await idempotency.check_and_set("order_1", {"status": "success"})
    assert is_duplicate is False

    # Duplicate request
    is_duplicate, cached = await idempotency.check_and_set("order_1")
    assert is_duplicate is True
    assert cached == {"status": "success"}


@pytest.mark.asyncio
async def test_ttl_expiration(idempotency):
    """Test that cache entries expire after TTL."""
    # Set a result
    await idempotency.check_and_set("order_1", {"status": "success"})

    # Wait for TTL to expire
    await asyncio.sleep(2.5)

    # Should be treated as new order
    is_duplicate, cached = await idempotency.check_and_set("order_1")
    assert is_duplicate is False
    assert cached is None


@pytest.mark.asyncio
async def test_set_result(idempotency):
    """Test setting result after execution."""
    # Check (new order)
    is_duplicate, _ = await idempotency.check_and_set("order_1")
    assert is_duplicate is False

    # Set result after execution
    await idempotency.set_result("order_1", {"status": "success", "order_id": "123"})

    # Check again (should be duplicate now)
    is_duplicate, cached = await idempotency.check_and_set("order_1")
    assert is_duplicate is True
    assert cached["status"] == "success"
    assert cached["order_id"] == "123"


@pytest.mark.asyncio
async def test_get_result(idempotency):
    """Test retrieving cached result."""
    result = {"status": "success", "order_id": "456"}
    await idempotency.set_result("order_1", result)

    cached = await idempotency.get_result("order_1")
    assert cached == result


@pytest.mark.asyncio
async def test_get_expired_result(idempotency):
    """Test that expired results return None."""
    await idempotency.set_result("order_1", {"status": "success"})

    # Wait for TTL to expire
    await asyncio.sleep(2.5)

    cached = await idempotency.get_result("order_1")
    assert cached is None


@pytest.mark.asyncio
async def test_clear(idempotency):
    """Test clearing all cached results."""
    await idempotency.set_result("order_1", {"status": "success"})
    await idempotency.set_result("order_2", {"status": "success"})

    assert idempotency.get_cache_size() == 2

    await idempotency.clear()

    assert idempotency.get_cache_size() == 0


@pytest.mark.asyncio
async def test_concurrent_access(idempotency):
    """Test concurrent access to idempotency handler."""
    async def check_order(order_id):
        return await idempotency.check_and_set(order_id, {"status": "success"})

    # Run multiple concurrent checks for the same order
    results = await asyncio.gather(*[check_order("order_1") for _ in range(5)])

    # First should be new, rest should be duplicates
    assert results[0][0] is False  # First is not duplicate
    for is_duplicate, _ in results[1:]:
        assert is_duplicate is True  # Rest are duplicates
