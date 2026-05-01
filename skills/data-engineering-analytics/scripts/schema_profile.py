#!/usr/bin/env python3
"""Profile schemas, tables, columns, constraints, indexes, and FK metadata."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

SYSTEM_SCHEMAS = {"information_schema", "pg_catalog", "pg_toast"}


def dsn_from_env_file() -> str:
    dsn_file = os.environ.get("MAISTACK_ANALYTICS_DSN_FILE")
    if not dsn_file:
        raise ValueError("MAISTACK_ANALYTICS_DSN_FILE is not set")
    return Path(dsn_file).read_text(encoding="utf-8").strip()


def fetch_all(cur, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, params)
    columns = [desc.name for desc in cur.description or []]
    return [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]


def profile_database(include_schemas: list[str] | None = None) -> dict[str, Any]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on sandbox image.
        raise RuntimeError("psycopg is required in the sandbox runtime") from exc

    include = set(include_schemas or [])
    dsn = dsn_from_env_file()
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("set transaction read only")
            # PostgreSQL doesn't accept parameter placeholders inside SET; the
            # value must be a literal. 30000ms is a hardcoded constant here,
            # so f-string interpolation is safe.
            cur.execute("set local statement_timeout = 30000")
            schemas = fetch_all(
                cur,
                """
                select schema_name
                from information_schema.schemata
                where schema_name not like 'pg_%'
                  and schema_name <> all(%s)
                order by schema_name
                """,
                (list(SYSTEM_SCHEMAS),),
            )
            schema_names = [row["schema_name"] for row in schemas if not include or row["schema_name"] in include]
            tables = fetch_all(
                cur,
                """
                select table_schema, table_name, table_type
                from information_schema.tables
                where table_schema = any(%s)
                order by table_schema, table_name
                """,
                (schema_names,),
            )
            columns = fetch_all(
                cur,
                """
                select table_schema, table_name, column_name, ordinal_position, data_type,
                       udt_name, is_nullable, column_default
                from information_schema.columns
                where table_schema = any(%s)
                order by table_schema, table_name, ordinal_position
                """,
                (schema_names,),
            )
            row_estimates = fetch_all(
                cur,
                """
                select n.nspname as table_schema, c.relname as table_name,
                       greatest(c.reltuples::bigint, 0) as estimated_rows
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = any(%s)
                  and c.relkind in ('r','p','v','m')
                order by n.nspname, c.relname
                """,
                (schema_names,),
            )
            constraints = fetch_all(
                cur,
                """
                select tc.table_schema, tc.table_name, tc.constraint_name, tc.constraint_type,
                       kcu.column_name, ccu.table_schema as foreign_table_schema,
                       ccu.table_name as foreign_table_name, ccu.column_name as foreign_column_name
                from information_schema.table_constraints tc
                left join information_schema.key_column_usage kcu
                  on tc.constraint_schema = kcu.constraint_schema
                 and tc.constraint_name = kcu.constraint_name
                left join information_schema.constraint_column_usage ccu
                  on tc.constraint_schema = ccu.constraint_schema
                 and tc.constraint_name = ccu.constraint_name
                where tc.table_schema = any(%s)
                order by tc.table_schema, tc.table_name, tc.constraint_name, kcu.ordinal_position
                """,
                (schema_names,),
            )
            indexes = fetch_all(
                cur,
                """
                select schemaname as table_schema, tablename as table_name, indexname, indexdef
                from pg_indexes
                where schemaname = any(%s)
                order by schemaname, tablename, indexname
                """,
                (schema_names,),
            )
            conn.rollback()
    return {
        "schemas": schema_names,
        "tables": tables,
        "columns": columns,
        "rowEstimates": row_estimates,
        "constraints": constraints,
        "indexes": indexes,
        "warnings": ["Row counts are PostgreSQL planner estimates, not exact counts."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", action="append", dest="schemas")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    profile = profile_database(args.schemas)
    payload = json.dumps(profile, indent=2, default=str)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
