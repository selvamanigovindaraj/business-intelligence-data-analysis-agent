from __future__ import annotations

from langchain_core.tools import tool


@tool
def get_stock_price(ticker: str) -> dict:
    """Fetch current price and basic fundamentals for *ticker*."""
    raise NotImplementedError


@tool
def get_financial_statements(ticker: str, period: str = "annual") -> dict:
    """Retrieve income statement, balance sheet, and cash flow for *ticker*."""
    raise NotImplementedError
