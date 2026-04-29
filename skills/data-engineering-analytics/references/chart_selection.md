# Chart Selection

Classify the question first, then use the shape of the result set.

## Request Classes

- Trend: how a metric changes over time.
- Comparison: ranking or comparing groups.
- Composition: contribution to a total.
- Distribution: spread, skew, outliers.
- Relationship: correlation or association between fields.
- Anomaly/root-cause: detect what changed and explain likely drivers.
- Segmentation: compare groups across customer, product, geography, or other dimensions.
- Data-quality: completeness, uniqueness, freshness, validity, referential integrity.
- Schema exploration: tables, columns, keys, joins, lineage.

## Chart Rules

- time + metric: line, area, or bar. Use line for continuous periods, bar for sparse periods.
- category + metric: sorted bar. Use horizontal bars for long labels.
- few categories + total: pie only when there are few categories and the question is explicitly share-of-total.
- numeric field: histogram or boxplot.
- two numeric fields: scatter.
- two dimensions + metric: heatmap.
- hierarchy: treemap or sunburst.
- flow or multi-step contribution: sankey.
- schema relationships: graph.

## Interaction Rules

Use `crossFilter` when a selected value should filter linked blocks. Use `drilldown` when the next level of detail is clear from the semantic model. Use `brush` for time ranges or numeric ranges. Use `highlight` for hover or selection emphasis. Use `compare` for side-by-side selected segments. Always provide `reset` when filters or drilldowns are present.
