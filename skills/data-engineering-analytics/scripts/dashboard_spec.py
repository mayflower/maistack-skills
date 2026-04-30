#!/usr/bin/env python3
"""Build flexible GenUI dashboard specs from query result JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CAPABILITIES_PATH = Path(__file__).resolve().parents[1] / "capabilities" / "data_engineering_dashboard_capabilities.json"
CHART_CAPABILITIES = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))["chartTypes"]
CHART_BY_ANALYSIS = {
    "trend": "line",
    "comparison": "bar",
    "composition": "bar",
    "distribution": "bar",
    "relationship": "scatter",
    "segmentation": "bar",
    "data-quality": "bar",
    "schema exploration": "graph",
}


def build_spec(
    *,
    title: str,
    question: str,
    analysis_type: str,
    datasets: list[dict[str, Any]],
    queries: list[dict[str, Any]] | None = None,
    insights: list[dict[str, Any]] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    for index, dataset in enumerate(datasets):
        dataset_id = dataset["id"]
        columns = dataset.get("columns") or _infer_columns(dataset.get("rows", []))
        chart_type = _supported_chart_type(CHART_BY_ANALYSIS.get(analysis_type, "bar"))
        if dataset.get("rows"):
            blocks.append({
                "id": f"chart_{index + 1}",
                "type": "chart",
                "title": dataset.get("title") or f"{title} chart",
                "dataset": dataset_id,
                "chart": {"type": chart_type, "encoding": _infer_encoding(dataset.get("rows", []), columns, chart_type, analysis_type)},
                "interactions": [{"type": "crossFilter", "event": "click", "field": columns[0] if columns else None, "targetBlocks": [f"table_{index + 1}"]}],
            })
        blocks.append({"id": f"table_{index + 1}", "type": "table", "title": dataset.get("title") or "Detail rows", "dataset": dataset_id})
    if insights:
        blocks.insert(0, {"id": "summary", "type": "textInsight", "title": "Summary", "content": insights[0].get("summary") or insights[0].get("text") or ""})
    return {
        "schemaVersion": "1.0",
        "title": title,
        "question": question,
        "analysisType": analysis_type,
        "audience": "analyst",
        "dataSources": [],
        "datasets": datasets,
        "parameters": [],
        "layout": {"columns": 12},
        "blocks": blocks,
        "interactions": [{"type": "reset"}] if blocks else [],
        "queries": queries or [],
        "insights": insights or [],
        "provenance": provenance or {},
    }


def _infer_columns(rows: list[dict[str, Any]]) -> list[str]:
    return list(rows[0].keys()) if rows else []


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _supported_chart_type(chart_type: str) -> str:
    return chart_type if chart_type in CHART_CAPABILITIES else "bar"


def _column_named(columns: list[str], *names: str) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for name in names:
        if name in lowered:
            return lowered[name]
    return None


def _infer_encoding(rows: list[dict[str, Any]], columns: list[str], chart_type: str, analysis_type: str) -> dict[str, Any]:
    numeric = [column for column in columns if any(_is_number(row.get(column)) for row in rows)]
    categorical = [column for column in columns if column not in numeric]
    if analysis_type == "relationship" and len(numeric) >= 2:
        return {"x": numeric[0], "y": numeric[1]}
    if chart_type in {"graph", "sankey", "lines"}:
        return {
            "source": _column_named(columns, "source", "from") or columns[0],
            "target": _column_named(columns, "target", "to") or (columns[1] if len(columns) > 1 else columns[0]),
            "value": (numeric or columns or [""])[0],
        }
    if chart_type == "heatmap":
        return {"x": (categorical or columns or [""])[0], "y": (categorical[1:] or columns or [""])[0], "value": (numeric or columns or [""])[0]}
    return {"x": (categorical or columns or [""])[0], "y": (numeric or columns or [""])[0]}


def load_dataset(path: Path, dataset_id: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "rows" in payload:
        return {"id": dataset_id, "columns": payload.get("columns") or _infer_columns(payload["rows"]), "rows": payload["rows"], "rowCount": payload.get("rowCount", len(payload["rows"]))}
    if isinstance(payload, list):
        return {"id": dataset_id, "columns": _infer_columns(payload), "rows": payload, "rowCount": len(payload)}
    raise ValueError("dataset JSON must be a readonly_query result or an array of rows")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--analysis-type", required=True)
    parser.add_argument("--dataset-json", type=Path, required=True)
    parser.add_argument("--dataset-id", default="result")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dataset = load_dataset(args.dataset_json, args.dataset_id)
    spec = build_spec(title=args.title, question=args.question, analysis_type=args.analysis_type, datasets=[dataset], provenance={"rowLimit": dataset.get("rowCount")})
    payload = json.dumps(spec, indent=2, default=str)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
