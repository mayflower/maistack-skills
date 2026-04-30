# Chart Selection

Classify the question first, then use the shape of the result set.

Use `../capabilities/data_engineering_dashboard_capabilities.json` as the source of truth for chart types, variants, required encodings, and supported interactions. Do not emit chart types outside that file. `custom` ECharts series are intentionally unsupported in dashboard specs because specs must not serialize executable `renderItem` functions; pre-registered reviewed custom series can be added later as explicit named capabilities.

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
- flow, circular dependency, or multi-step contribution: sankey or chord. Prefer chord when bidirectional or many-to-many relationships are the main message.
- schema relationships: graph.
- financial open/high/low/close: candlestick.
- five-number summary by group: boxplot.
- multi-metric entity profile: radar.
- pipeline or stage conversion: funnel.
- single KPI against target: gauge.
- geospatial region values: map only when a registered map is available.
- overlapping scatter groups: scatter with the `jitter` or `beeswarm` variant.
- coordinated nested views: use `coordinateSystem: matrix` only when the dashboard needs a deliberate ECharts 6 matrix coordinate layout.

## Interaction Rules

Use `crossFilter` when a selected value should filter linked blocks. Use `drilldown` when the next level of detail is clear from the semantic model. Use `brush` for time ranges or numeric ranges. Use `highlight` for hover or selection emphasis. Use `compare` for side-by-side selected segments. Always provide `reset` when filters or drilldowns are present.
