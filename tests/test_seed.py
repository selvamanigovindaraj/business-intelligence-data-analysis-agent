from __future__ import annotations

from scripts.seed import _build_documents, _ColumnInfo, _TableDescriptions


def test_build_documents_includes_column_schema_in_metadata() -> None:
    columns = [_ColumnInfo("order_id", "integer"), _ColumnInfo("customer_id", "character varying")]
    descriptions = _TableDescriptions(
        table_description="Stores orders.",
        columns={"order_id": "Primary key.", "customer_id": "FK to customers."},
    )
    docs = _build_documents("orders", columns, descriptions)

    assert len(docs) == 1
    meta = docs[0].metadata
    assert meta["columns"] == [
        {"name": "order_id", "data_type": "integer"},
        {"name": "customer_id", "data_type": "character varying"},
    ]
