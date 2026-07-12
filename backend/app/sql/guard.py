"""Defense-in-depth validation for LLM-generated SQL.

Two independent layers, deliberately redundant:
  1. Static checks here (single statement, SELECT-only, table whitelist) --
     fast, gives the model a clear error message it can react to.
  2. `PRAGMA query_only = ON` set on the connection itself (see db.py) --
     the actual enforcement backstop. Even if a crafted query slips past the
     regex checks below (e.g. an edge case in tokenizing), SQLite itself
     refuses any write at the engine level.
Static analysis of SQL is inherently incomplete, and one hidden ATTACH or
subquery trick would only need to bypass one layer -- not both.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_TABLE = "orders"

_FORBIDDEN_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create",
    "attach", "detach", "pragma", "replace", "truncate", "vacuum",
    "reindex", "into", "grant", "revoke",
)


@dataclass
class SqlValidationResult:
    ok: bool
    sanitized_query: str | None = None
    error: str | None = None


def validate_and_sanitize(query: str, row_limit: int) -> SqlValidationResult:
    stripped = query.strip().rstrip(";").strip()

    if not stripped:
        return SqlValidationResult(ok=False, error="Empty query.")

    if ";" in stripped:
        return SqlValidationResult(ok=False, error="Only a single SQL statement is allowed.")

    if not re.match(r"(?is)^select\b", stripped):
        return SqlValidationResult(ok=False, error="Only SELECT statements are allowed.")

    lowered = stripped.lower()
    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            return SqlValidationResult(ok=False, error=f"Keyword '{keyword}' is not permitted.")

    if not re.search(rf"\bfrom\s+{ALLOWED_TABLE}\b", lowered):
        return SqlValidationResult(
            ok=False, error=f"Query must select from the '{ALLOWED_TABLE}' table only."
        )

    if not re.search(r"(?is)\blimit\s+\d+", stripped):
        stripped = f"{stripped} LIMIT {row_limit}"

    return SqlValidationResult(ok=True, sanitized_query=stripped)
