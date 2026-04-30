from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "data-engineering-analytics"


def load_script(name: str):
    path = SKILL_DIR / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readonly_query_accepts_select_and_cte() -> None:
    readonly_query = load_script("readonly_query.py")
    assert readonly_query.assert_readonly_sql("select 1") == "select 1"
    assert readonly_query.assert_readonly_sql("with rows as (select 1 as n) select n from rows").startswith("with rows")


def test_readonly_query_rejects_write_and_admin_sql() -> None:
    readonly_query = load_script("readonly_query.py")
    for sql in ["delete from sales", "select * from users; drop table users", "copy users to stdout", "set role postgres"]:
        try:
            readonly_query.assert_readonly_sql(sql)
        except ValueError:
            pass
        else:  # pragma: no cover - assertion branch
            raise AssertionError(f"SQL should have been rejected: {sql}")


def test_semantic_model_handles_fk_and_no_fk_profiles() -> None:
    semantic_model = load_script("semantic_model.py")
    profile = {
        "columns": [
            {"table_schema": "public", "table_name": "sales", "column_name": "product_id", "data_type": "integer"},
            {"table_schema": "public", "table_name": "sales", "column_name": "sales_amount", "data_type": "numeric"},
            {"table_schema": "public", "table_name": "sales", "column_name": "order_date", "data_type": "date"},
            {"table_schema": "public", "table_name": "products", "column_name": "product_id", "data_type": "integer"},
            {"table_schema": "public", "table_name": "products", "column_name": "category", "data_type": "text"},
        ],
        "rowEstimates": [
            {"table_schema": "public", "table_name": "sales", "estimated_rows": 50000},
            {"table_schema": "public", "table_name": "products", "estimated_rows": 100},
        ],
        "constraints": [
            {
                "table_schema": "public",
                "table_name": "sales",
                "constraint_type": "FOREIGN KEY",
                "column_name": "product_id",
                "foreign_table_schema": "public",
                "foreign_table_name": "products",
                "foreign_column_name": "product_id",
            }
        ],
    }
    model = semantic_model.infer_semantic_model(profile)
    assert any(table["kind"] == "fact" for table in model["tables"])
    assert any(join["source"] == "foreign_key" for join in model["joins"])

    no_fk = {**profile, "constraints": []}
    inferred = semantic_model.infer_semantic_model(no_fk)
    assert "No foreign keys were found" in inferred["warnings"][0]
    assert any(join["source"] == "name_match" for join in inferred["joins"])


def test_dashboard_spec_validation_rejects_executable_content() -> None:
    validator = load_script("validate_dashboard_spec.py")
    spec = {
        "schemaVersion": "1.0",
        "title": "Bad",
        "question": "Can this run code?",
        "analysisType": "schema exploration",
        "datasets": [],
        "blocks": [{"id": "bad", "type": "textInsight", "html": "<script>alert(1)</script>"}],
        "interactions": [],
        "queries": [],
        "insights": [],
        "provenance": {},
    }
    try:
        validator.validate(spec)
    except ValueError as exc:
        assert "forbidden" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("dashboard spec should reject executable content")


def test_dashboard_capabilities_are_reflected_in_json_schema() -> None:
    capabilities = json.loads((SKILL_DIR / "capabilities" / "data_engineering_dashboard_capabilities.json").read_text(encoding="utf-8"))
    schema = json.loads((SKILL_DIR / "schemas" / "dashboard_spec.schema.json").read_text(encoding="utf-8"))
    assert set(schema["$defs"]["chartType"]["enum"]) == set(capabilities["chartTypes"])
    assert "custom" in capabilities["unsupportedChartTypes"]
    assert "custom" not in capabilities["chartTypes"]


def test_dashboard_spec_validation_accepts_all_supported_chart_types() -> None:
    validator = load_script("validate_dashboard_spec.py")
    capabilities = json.loads((SKILL_DIR / "capabilities" / "data_engineering_dashboard_capabilities.json").read_text(encoding="utf-8"))
    for chart_type, capability in capabilities["chartTypes"].items():
        encoding = {key: key for key in capability["requiredEncodings"]}
        rows = [{key: index + 1 for index, key in enumerate(encoding)}]
        if "x" in encoding:
            rows[0]["x"] = "A"
        if "source" in encoding:
            rows[0]["source"] = "A"
            rows[0]["target"] = "B"
        if "dimensions" in encoding:
            encoding["dimensions"] = ["a", "b"]
            rows = [{"a": 1, "b": 2}]
        spec = {
            "schemaVersion": "1.0",
            "title": chart_type,
            "question": f"Can {chart_type} render?",
            "analysisType": "comparison",
            "datasets": [{"id": "result", "columns": list(rows[0]), "rows": rows}],
            "blocks": [{"id": "chart", "type": "chart", "dataset": "result", "chart": {"type": chart_type, "encoding": encoding}}],
            "interactions": [],
            "queries": [],
            "insights": [],
            "provenance": {},
        }
        assert validator.validate(spec) == spec


def test_dashboard_spec_validation_rejects_unknown_chart_type() -> None:
    validator = load_script("validate_dashboard_spec.py")
    spec = {
        "schemaVersion": "1.0",
        "title": "Bad",
        "question": "Can this render?",
        "analysisType": "comparison",
        "datasets": [{"id": "result", "columns": ["x", "y"], "rows": [{"x": "A", "y": 1}]}],
        "blocks": [{"id": "chart", "type": "chart", "dataset": "result", "chart": {"type": "custom", "encoding": {"x": "x", "y": "y"}}}],
        "interactions": [],
        "queries": [],
        "insights": [],
        "provenance": {},
    }
    try:
        validator.validate(spec)
    except ValueError as exc:
        assert "unsupported chart type" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("dashboard spec should reject unknown chart types")
