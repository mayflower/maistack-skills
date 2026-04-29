# Dashboard Strategy

The goal is not to produce a single chart. The goal is to answer the user's question with the right combination of evidence, interaction, and explanation.

## Communication Modes

- Answer-first dashboard: start with the answer, key metric, supporting chart, detail table, and assumptions.
- Investigation workspace: show a trend or anomaly first, then contribution, drilldown, segment comparison, detail records, and SQL/provenance.
- Exploration workspace: show schema context, candidate facts/dimensions, sample distributions, and suggested next drilldowns.
- Data-quality report: show completeness, uniqueness, row counts, freshness, validity warnings, and affected tables/columns.
- Schema/lineage view: show tables, joins, keys, likely facts/dimensions, and confidence warnings.

## Block Composition

A focused metric question can use 3 to 4 blocks. A broad analysis can use 6 to 10 blocks. Prefer small coordinated blocks over one overloaded chart.

Always include provenance sufficient for trust: source tables, row limits, query summaries, assumptions, warnings, semantic model confidence, and freshness where available. Never include credentials or DSNs.
