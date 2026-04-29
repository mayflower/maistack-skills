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
        for interaction in block.get("interactions", []):
            _validate_interaction(interaction, block_ids=None)

    for interaction in spec.get("interactions", []):
        _validate_interaction(interaction, block_ids=block_ids)

    _scan(spec)
    return spec


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
