from __future__ import annotations

import re
from typing import Any

import sqlparse
import sqlparse.tokens as T
from sqlparse.sql import Function, Identifier, IdentifierList

from app.models import TableSchema

_FROM_JOIN_RE = re.compile(r'\b(?:FROM|JOIN)\s+([a-zA-Z_]\w*)', re.IGNORECASE)

# Common SQL aggregate/scalar functions that appear as bare identifiers in SELECT.
_SQL_FUNCTIONS = frozenset({
    "count", "sum", "avg", "min", "max", "coalesce", "nullif", "round",
    "extract", "date_trunc", "now", "cast", "to_char", "upper", "lower",
    "trim", "length", "substring", "concat", "rank", "row_number", "dense_rank",
    "ntile", "lag", "lead", "first_value", "last_value",
})


def _extract_table_refs(sql: str) -> set[str]:
    return {m.group(1).lower() for m in _FROM_JOIN_RE.finditer(sql)}


def _extract_schema_columns(schemas: list[TableSchema]) -> set[str]:
    cols: set[str] = set()
    for s in schemas:
        for col in s.metadata.get("columns", []):
            if name := col.get("name"):
                cols.add(name.lower())
    return cols


# Any: sqlparse tokens share no common typed base
def _collect_select_cols(token: Any, cols: set[str]) -> None:
    if isinstance(token, IdentifierList):
        for ident in token.get_identifiers():
            _collect_select_cols(ident, cols)
    elif isinstance(token, Identifier):
        # table.col → get_real_name returns the column name (strips qualifier)
        # function call → first token is a Function instance → skip
        if isinstance(token.tokens[0], Function):
            return
        name = token.get_real_name()
        if name and name.lower() not in _SQL_FUNCTIONS:
            cols.add(name.lower())
    elif token.ttype is T.Wildcard:
        pass  # SELECT * is always valid


def _extract_select_cols(statement: sqlparse.sql.Statement) -> set[str]:
    cols: set[str] = set()
    in_select = False
    for token in statement.tokens:
        if token.ttype is T.DML and token.normalized.upper() == "SELECT":
            in_select = True
        elif in_select and token.ttype is T.Keyword and token.normalized.upper() == "FROM":
            break
        elif in_select and not token.is_whitespace:
            _collect_select_cols(token, cols)
    return cols


def validate_sql(sql: str, schemas: list[TableSchema]) -> str | None:
    # validates before execution to avoid unsafe DB round-trips
    if not sql.strip():
        return "Empty SQL statement"

    parsed = sqlparse.parse(sql.strip())
    if not parsed:
        return "Could not parse SQL"

    statement = parsed[0]
    stmt_type = statement.get_type()
    if stmt_type != "SELECT":
        return f"Only SELECT statements are allowed; got {stmt_type or 'unknown type'}"

    known_tables = {s.table.lower() for s in schemas}
    unknown_tables = _extract_table_refs(sql) - known_tables
    if unknown_tables:
        return f"Unknown table(s): {', '.join(sorted(unknown_tables))}"

    known_cols = _extract_schema_columns(schemas)
    if known_cols:
        unknown_cols = _extract_select_cols(statement) - known_cols
        if unknown_cols:
            return f"Unknown column(s): {', '.join(sorted(unknown_cols))}"

    return None
