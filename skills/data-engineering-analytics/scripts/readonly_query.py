#!/usr/bin/env python3
"""Run bounded read-only SQL against the analytics database."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BLOCKED_KEYWORDS = {
    "alter", "analyze", "attach", "call", "checkpoint", "comment", "copy", "create", "delete", "detach",
    "discard", "do", "drop", "execute", "grant", "insert", "listen", "load", "lock", "merge", "notify",
    "prepare", "reassign", "refresh", "reindex", "reset", "revoke", "security", "set", "truncate", "unlisten",
    "update", "vacuum",
}
COMMENT_RE = re.compile(r"(--[^\n]*|/\*.*?\*/)", re.S)


def dsn_from_env_file() -> str:
    dsn_file = os.environ.get("MAISTACK_ANALYTICS_DSN_FILE")
    if not dsn_file:
        raise ValueError("MAISTACK_ANALYTICS_DSN_FILE is not set")
    dsn = Path(dsn_file).read_text(encoding="utf-8").strip()
    if not dsn:
        raise ValueError("analytics DSN file is empty")
    return dsn


def normalize_sql(sql: str) -> str:
    return COMMENT_RE.sub(" ", sql).strip()


def assert_readonly_sql(sql: str) -> str:
    cleaned = normalize_sql(sql)
    if not cleaned:
        raise ValueError("SQL is empty")
    statements = [part.strip() for part in cleaned.split(";") if part.strip()]
    if len(statements) != 1:
        raise ValueError("only one SELECT/CTE statement is allowed")
    statement = statements[0]
    first = statement.split(None, 1)[0].lower()
    if first not in {"select", "with"}:
        raise ValueError("only SELECT or WITH queries are allowed")
    tokens = set(re.findall(r"\b[a-z_]+\b", statement.lower()))
    blocked = sorted(tokens & BLOCKED_KEYWORDS)
    if blocked:
        raise ValueError(f"blocked read-only SQL keyword(s): {', '.join(blocked)}")
    return statement


def execute_readonly(sql: str, *, limit: int = 5000, timeout_ms: int = 30000) -> dict[str, Any]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on sandbox image.
        raise RuntimeError("psycopg is required in the sandbox runtime") from exc

    statement = assert_readonly_sql(sql)
    limit = max(1, min(limit, 100000))
    timeout_ms = max(1000, min(timeout_ms, 300000))
    wrapped_sql = f"select * from ({statement}) as maistack_readonly_query limit %s"
    dsn = dsn_from_env_file()
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("set local statement_timeout = %s", (timeout_ms,))
            cur.execute(wrapped_sql, (limit,))
            columns = [desc.name for desc in cur.description or []]
            rows = [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]
            conn.rollback()
    return {"columns": columns, "rows": rows, "rowCount": len(rows), "limit": limit, "truncated": len(rows) >= limit}


def write_output(result: dict[str, Any], output: Path | None, output_format: str) -> None:
    if output_format == "csv":
        handle = output.open("w", newline="", encoding="utf-8") if output else sys.stdout
        close = output is not None
        try:
            writer = csv.DictWriter(handle, fieldnames=result.get("columns", []))
            writer.writeheader()
            writer.writerows(result.get("rows", []))
        finally:
            if close:
                handle.close()
        return
    payload = json.dumps(result, indent=2, default=str)
    if output:
        output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--sql")
    source.add_argument("--sql-file", type=Path)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sql = args.sql if args.sql is not None else args.sql_file.read_text(encoding="utf-8")
    try:
        result = execute_readonly(sql, limit=args.limit, timeout_ms=args.timeout_ms)
        write_output(result, args.output, args.format)
    except Exception as exc:  # noqa: BLE001 - CLI should print validation error cleanly.
        print(f"query failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
