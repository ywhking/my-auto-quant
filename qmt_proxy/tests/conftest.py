"""Configuration for pytest tests."""

import sys
from pathlib import Path

import pytest

# Add project root and src to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def reset_connections():
    """Reset all connections before each test."""
    from qmt_proxy.connection_manager import _connections

    _connections.clear()
    yield
