#!/usr/bin/env python3
"""Validate a data engineering dashboard spec without executing any spec content."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BLOCK_TYPES = {"metric", "chart", "table", "textInsight", "sql", "dataQuality", "relationshipMap", "filterControl"}
INTERACTION_TYPES = {"crossFilter", "drilldown", "brush", "highlight", "compare", "reset"}
CAPABILITIES_PATH = Path(__file__).resolve().parents[1] / "capabilities" / "data_engineering_dashboard_capabilities.json"
CHART_CAPABILITIES = json.loads(CAPABILITIES_PATH.read_text(encoding="utf-8"))["chartTypes"]
INFERABLE_ENCODINGS = {"x", "y"}
FORBIDDEN_KEYS = {
    "dangerouslySetInnerHTML",
    "html",
    "innerHTML",
    "javascript",
    "onerror",
    "onload",
    "script",
    "srcdoc",
    "widget_code",
}
FORBIDDEN_PATTERNS = [re.compile(r"<\s*script", re.I), re.compile(r"javascript\s*:", re.I)]


def _fail(message: str) -> None:
    raise ValueError(message)


def _scan(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS or (key.lower().startswith("on") and len(key) > 2):
                _fail(f"forbidden executable key at {path}.{key}")
            _scan(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan(child, f"{path}[{index}]")
    elif isinstance(value, str):
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(value):
                _fail(f"forbidden executable string at {path}")


def validate(spec: dict[str, Any]) -> dict[str, Any]:
    required = ["schemaVersion", "title", "question", "analysisType", "datasets", "blocks", "interactions", "queries", "insights", "provenance"]
    for key in required:
        if key not in spec:
            _fail(f"missing required field: {key}")
    if not isinstance(spec.get("datasets"), list):
        _fail("datasets must be an array")
    if not isinstance(spec.get("blocks"), list):
        _fail("blocks must be an array")

    dataset_ids = set()
    for dataset in spec["datasets"]:
        if not isinstance(dataset, dict) or not dataset.get("id"):
            _fail("every dataset must have an id")
        dataset_ids.add(dataset["id"])

    block_ids = set()
    for block in spec["blocks"]:
        if not isinstance(block, dict):
            _fail("every block must be an object")
        block_id = block.get("id")
        if not block_id:
            _fail("every block must have an id")
        if block_id in block_ids:
            _fail(f"duplicate block id: {block_id}")
        block_ids.add(block_id)
        if block.get("type") not in BLOCK_TYPES:
            _fail(f"unsupported block type: {block.get('type')}")
        dataset = block.get("dataset")
        if dataset and dataset not in dataset_ids:
            _fail(f"block {block_id} references unknown dataset {dataset}")
        if block.get("type") == "chart":
            _validate_chart(block)
        for interaction in block.get("interactions", []):
            _validate_interaction(interaction, block_ids=None)

    for interaction in spec.get("interactions", []):
        _validate_interaction(interaction, block_ids=block_ids)

    _scan(spec)
    return spec


def _chart_type(chart: Any) -> str | None:
    if isinstance(chart, str):
        return chart
    if isinstance(chart, dict) and isinstance(chart.get("type"), str):
        return chart["type"]
    return None


def _chart_encoding(chart: Any) -> dict[str, Any]:
    if not isinstance(chart, dict):
        return {}
    encoding = chart.get("encoding")
    return encoding if isinstance(encoding, dict) else {}


def _validate_chart(block: dict[str, Any]) -> None:
    chart_type = _chart_type(block.get("chart"))
    if not chart_type:
        _fail(f"chart block {block['id']} must declare chart.type")
    capability = CHART_CAPABILITIES.get(chart_type)
    if not capability:
        _fail(f"unsupported chart type: {chart_type}")
    encoding = _chart_encoding(block.get("chart"))
    for key, value in encoding.items():
        if not isinstance(key, str):
            _fail(f"invalid encoding key in block {block['id']}")
        if not isinstance(value, str) and not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
            _fail(f"invalid encoding value in block {block['id']}")
    missing = sorted(set(capability.get("requiredEncodings", [])) - set(encoding) - INFERABLE_ENCODINGS)
    if missing:
        _fail(f"chart block {block['id']} missing required encodings: {', '.join(missing)}")


def _validate_interaction(interaction: Any, block_ids: set[str] | None) -> None:
    if not isinstance(interaction, dict):
        _fail("interaction must be an object")
    if interaction.get("type") not in INTERACTION_TYPES:
        _fail(f"unsupported interaction type: {interaction.get('type')}")
    if block_ids is not None:
        for target in interaction.get("targetBlocks", []) or []:
            if target not in block_ids:
                _fail(f"interaction references unknown target block {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    args = parser.parse_args()
    try:
        validate(json.loads(args.spec.read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001 - CLI should print validation error cleanly.
        print(f"invalid dashboard spec: {exc}", file=sys.stderr)
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
