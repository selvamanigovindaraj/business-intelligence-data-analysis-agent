from __future__ import annotations

from app.agents.tools.sql_validator import validate_sql
from app.models import TableSchema

_SCHEMAS = [
    TableSchema(
        table="orders",
        content="Table: orders\nStores orders.",
        metadata={
            "columns": [
                {"name": "order_id", "data_type": "integer"},
                {"name": "customer_id", "data_type": "character varying"},
                {"name": "freight", "data_type": "real"},
            ]
        },
    ),
    TableSchema(
        table="customers",
        content="Table: customers\nStores customers.",
        metadata={
            "columns": [
                {"name": "customer_id", "data_type": "character varying"},
                {"name": "company_name", "data_type": "character varying"},
            ]
        },
    ),
]


def test_valid_select_passes() -> None:
    assert validate_sql("SELECT order_id FROM orders", _SCHEMAS) is None


def test_star_select_passes() -> None:
    assert validate_sql("SELECT * FROM orders", _SCHEMAS) is None


def test_join_known_tables_passes() -> None:
    sql = (
        "SELECT o.order_id, c.company_name "
        "FROM orders o JOIN customers c ON o.customer_id = c.customer_id"
    )
    assert validate_sql(sql, _SCHEMAS) is None


def test_empty_sql_fails() -> None:
    err = validate_sql("", _SCHEMAS)
    assert err is not None
    assert "empty" in err.lower()


def test_non_select_fails() -> None:
    err = validate_sql("DELETE FROM orders WHERE order_id = 1", _SCHEMAS)
    assert err is not None
    assert "SELECT" in err


def test_unknown_table_fails() -> None:
    err = validate_sql("SELECT * FROM products", _SCHEMAS)
    assert err is not None
    assert "products" in err


def test_join_unknown_table_fails() -> None:
    err = validate_sql(
        "SELECT * FROM orders JOIN products ON orders.order_id = products.order_id",
        _SCHEMAS,
    )
    assert err is not None
    assert "products" in err


def test_unknown_column_fails() -> None:
    err = validate_sql("SELECT nonexistent_col FROM orders", _SCHEMAS)
    assert err is not None
    assert "nonexistent_col" in err


def test_qualified_column_passes() -> None:
    assert validate_sql("SELECT o.order_id FROM orders o", _SCHEMAS) is None


def test_aggregate_function_passes() -> None:
    assert validate_sql("SELECT COUNT(*), SUM(freight) FROM orders", _SCHEMAS) is None
