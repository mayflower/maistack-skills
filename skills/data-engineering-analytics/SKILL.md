---
name: data-engineering-analytics
description: Generic read-only data engineering analytics skill that profiles SQL databases, infers semantic models, runs safe queries, and emits interactive GenUI dashboard specs.
license: MIT
metadata:
  version: 1.0.0
  category: analytics
  domain: data-engineering
  updated: 2026-04-29
  python-tools: schema_profile.py, readonly_query.py, semantic_model.py, dashboard_spec.py, validate_dashboard_spec.py
---

# Data Engineering Analytics

Use this skill whenever the user asks to inspect, explain, analyze, profile, quality-check, or visualize data from the connected analytics database. The database is generic. AdventureWorks is only a demo dataset and must never be assumed in executable code.

## Operating Contract

- Read the connection string only from the file path in `MAISTACK_ANALYTICS_DSN_FILE`.
- Never print, echo, store, include, or summarize credentials or DSNs in chat, artifacts, dashboard specs, logs, SQL blocks, or provenance.
- Treat the database as read-only. Use `scripts/readonly_query.py` for SQL execution unless the user explicitly asks only for a draft query.
- Use database metadata first, then infer a semantic model before choosing queries or charts.
- Do not assume table names, schemas, measures, joins, or date columns. Infer them from metadata and query samples.
- Use `data_engineering_show_dashboard` for interactive dashboards. Use `visualize_show_widget` only as a fallback for one-off custom HTML widgets.
- Dashboard specs must be JSON data only. Do not put HTML, JavaScript, event handler names, scripts, or executable code in the spec.
- Choose chart types and coordinate systems only from `capabilities/data_engineering_dashboard_capabilities.json`. Do not invent ECharts chart types or use unsupported custom renderers.

## Workflow

1. Profile the connected database:

```bash
python scripts/schema_profile.py --output /tmp/analytics_schema_profile.json
```

2. Infer the semantic model:

```bash
python scripts/semantic_model.py /tmp/analytics_schema_profile.json --output /tmp/analytics_semantic_model.json
```

3. Classify the user request as one or more of: trend, comparison, composition, distribution, relationship, anomaly/root-cause, segmentation, data-quality, schema exploration.

4. Choose the communication mode:

- `answer-first dashboard` for focused business questions.
- `investigation workspace` for root-cause, anomaly, and exploratory questions.
- `exploration workspace` for broad or ambiguous analysis.
- `data-quality report` for validation, profiling, completeness, uniqueness, and freshness.
- `schema/lineage view` for metadata, relationship, and model questions.

5. Run only the minimum safe SQL needed. Prefer aggregate queries and bounded samples.

```bash
python scripts/readonly_query.py --sql-file /tmp/query.sql --limit 5000 --output /tmp/query_result.json
```

6. Build and validate a dashboard spec:

```bash
python scripts/dashboard_spec.py --title "Analysis" --question "$USER_QUESTION" --analysis-type trend --dataset-json /tmp/query_result.json --output /tmp/dashboard.json
python scripts/validate_dashboard_spec.py /tmp/dashboard.json
```

7. Call `data_engineering_show_dashboard` with the validated spec. The response should explain the answer, assumptions, warnings, and next useful drilldowns without exposing secrets.

## Dashboard Strategy

A narrow question may need one metric, one chart, one table, and a short explanation. A broad investigation should include multiple coordinated blocks such as trend, contribution, drilldown, detail table, SQL, data-quality, and provenance.

The skill chooses the number and type of blocks from the question and data shape. It should not use a fixed dashboard layout.

Use the references:

- `capabilities/data_engineering_dashboard_capabilities.json` for the exact chart types, required encodings, variants, and supported interactions implemented by the widget.
- `references/dashboard_strategy.md` for communication strategy.
- `references/chart_selection.md` for chart selection rules.
- `references/examples/adventureworks_dw.md` only as optional demo guidance.

## GenUI Dashboard Rules

The dashboard spec supports these block types: `metric`, `chart`, `table`, `textInsight`, `sql`, `dataQuality`, `relationshipMap`, `filterControl`.

The dashboard spec supports these interactions: `crossFilter`, `drilldown`, `brush`, `highlight`, `compare`, `reset`.

The frontend owns ECharts rendering and event handling. The skill declares intent, data, encodings, joins, assumptions, and warnings. It does not emit JavaScript.

For interactive exploration, use the capability manifest's `interactiveExploration` section as the contract. The widget supports ECharts `tooltip`, `legend`, `dataZoom`, `brush`, `visualMap`, and `toolbox`; it translates click events to equality filters, brush selections to set filters, data zoom ranges to range filters, and legend selection changes to grouped set filters. Declare interactions when linked blocks should react to selections, and include a `filterControl` block when a dashboard is meant to be explored rather than only read.

Every chart block must declare `chart.type` and, for specialized charts, the required `chart.encoding` fields from the capability manifest. Basic `x`/`y` encodings may be inferred from result columns, but explicit encodings are preferred for all production dashboard specs.
