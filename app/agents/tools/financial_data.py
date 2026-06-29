from __future__ import annotations

from typing import Any

from langchain_core.tools import tool


@tool
def get_stock_price(ticker: str) -> dict[str, Any]:
    """Fetch current price and basic fundamentals for *ticker*."""
    raise NotImplementedError


@tool
def get_financial_statements(ticker: str, period: str = "annual") -> dict[str, Any]:
    """Retrieve income statement, balance sheet, and cash flow for *ticker*."""
    raise NotImplementedError
