#!/usr/bin/env python3
"""Infer a lightweight semantic model from a schema profile."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

NUMERIC_TYPES = {"integer", "bigint", "smallint", "numeric", "decimal", "real", "double precision", "money"}
TIME_HINTS = ("date", "time", "year", "month", "quarter", "week")
MEASURE_HINTS = ("amount", "total", "sales", "revenue", "cost", "price", "qty", "quantity", "count", "margin")
DIMENSION_HINTS = ("name", "category", "type", "status", "city", "country", "region", "segment", "group")


def _table_key(row: dict[str, Any]) -> str:
    return f"{row.get('table_schema')}.{row.get('table_name')}"


def infer_semantic_model(profile: dict[str, Any]) -> dict[str, Any]:
    columns_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    row_estimates = {_table_key(row): int(row.get("estimated_rows") or 0) for row in profile.get("rowEstimates", [])}
    for column in profile.get("columns", []):
        columns_by_table[_table_key(column)].append(column)

    constraints = profile.get("constraints", [])
    fk_edges = [row for row in constraints if row.get("constraint_type") == "FOREIGN KEY" and row.get("foreign_table_name")]
    referenced_tables = {f"{row.get('foreign_table_schema')}.{row.get('foreign_table_name')}" for row in fk_edges}
    referencing_tables = {_table_key(row) for row in fk_edges}

    tables = []
    for table, columns in sorted(columns_by_table.items()):
        numeric_columns = [c["column_name"] for c in columns if str(c.get("data_type", "")).lower() in NUMERIC_TYPES]
        time_columns = [c["column_name"] for c in columns if any(hint in str(c.get("column_name", "")).lower() for hint in TIME_HINTS)]
        measure_columns = [c for c in numeric_columns if any(hint in c.lower() for hint in MEASURE_HINTS)]
        dimension_columns = [c["column_name"] for c in columns if any(hint in str(c.get("column_name", "")).lower() for hint in DIMENSION_HINTS)]
        name = table.lower()
        fact_score = 0
        fact_score += 2 if table in referencing_tables else 0
        fact_score += 1 if any(token in name for token in ("fact", "transaction", "sales", "order", "event", "line")) else 0
        fact_score += 1 if len(measure_columns) >= 1 else 0
        fact_score += 1 if row_estimates.get(table, 0) > 10000 else 0
        dimension_score = 0
        dimension_score += 2 if table in referenced_tables else 0
        dimension_score += 1 if any(token in name for token in ("dim", "dimension", "lookup", "category", "customer", "product")) else 0
        dimension_score += 1 if dimension_columns else 0
        kind = "fact" if fact_score > dimension_score else "dimension" if dimension_score > 0 else "table"
        confidence = min(0.95, 0.35 + 0.12 * max(fact_score, dimension_score))
        tables.append({
            "table": table,
            "kind": kind,
            "confidence": round(confidence, 2),
            "estimatedRows": row_estimates.get(table),
            "grainCandidates": _grain_candidates(table, columns, constraints),
            "measures": measure_columns,
            "numericColumns": numeric_columns,
            "timeColumns": time_columns,
            "dimensionColumns": dimension_columns[:20],
        })

    joins = []
    for edge in fk_edges:
        joins.append({
            "fromTable": _table_key(edge),
            "fromColumn": edge.get("column_name"),
            "toTable": f"{edge.get('foreign_table_schema')}.{edge.get('foreign_table_name')}",
            "toColumn": edge.get("foreign_column_name"),
            "confidence": 0.95,
            "source": "foreign_key",
        })
    joins.extend(_name_based_join_candidates(columns_by_table, joins))

    warnings = []
    if not fk_edges:
        warnings.append("No foreign keys were found. Joins are inferred from column names with lower confidence.")
    if not any(table["kind"] == "fact" for table in tables):
        warnings.append("No high-confidence fact table was inferred. Start with schema exploration or bounded samples.")

    return {"tables": tables, "joins": joins, "warnings": warnings}


def _grain_candidates(table: str, columns: list[dict[str, Any]], constraints: list[dict[str, Any]]) -> list[str]:
    keys = [row.get("column_name") for row in constraints if _table_key(row) == table and row.get("constraint_type") in {"PRIMARY KEY", "UNIQUE"}]
    if keys:
        return [str(key) for key in keys if key]
    id_like = [column["column_name"] for column in columns if re.search(r"(^id$|_id$|key$)", str(column.get("column_name", "")).lower())]
    return id_like[:5]


def _name_based_join_candidates(columns_by_table: dict[str, list[dict[str, Any]]], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing_pairs = {(join["fromTable"], join["fromColumn"], join["toTable"], join["toColumn"]) for join in existing}
    columns = []
    for table, table_columns in columns_by_table.items():
        for column in table_columns:
            name = str(column.get("column_name", "")).lower()
            if name.endswith("_id") or name.endswith("key") or name == "id":
                columns.append((table, column.get("column_name")))
    candidates = []
    for left_table, left_column in columns:
        for right_table, right_column in columns:
            if left_table >= right_table or left_column != right_column:
                continue
            pair = (left_table, left_column, right_table, right_column)
            if pair not in existing_pairs:
                candidates.append({
                    "fromTable": left_table,
                    "fromColumn": left_column,
                    "toTable": right_table,
                    "toColumn": right_column,
                    "confidence": 0.45,
                    "source": "name_match",
                })
    return candidates[:200]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    model = infer_semantic_model(json.loads(args.profile.read_text(encoding="utf-8")))
    payload = json.dumps(model, indent=2, default=str)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
