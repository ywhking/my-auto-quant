"""Main entry point for trader_executor module.

Allows running the executor client as a standalone module:
    python -m trader_executor

Or directly:
    python trader_executor/__main__.py
"""

from trader_executor.main import main

if __name__ == "__main__":
    main()
