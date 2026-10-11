---
title: Control Model
aliases:
  - control-model
  - architecture/control_model
tags:
  - architecture
  - platform
  - validation
source: docs/architecture/control_model.md
type: spec
---

> **Related:**
- [[Workflows/Demo Ingestion Workflow]]
- [[Architecture/Tolkien Overview]]
- [[Meta/Data Layout]]
- [[Home]]

# Multimodal Platform Control Model

This project uses research-grade controls that can mature toward regulated
research workflows without changing the core data model.

## Validation Controls

Validation gates are executable checks over canonical CSV/Parquet tables.
Failed error-level checks block downstream publication of artifacts.

Minimum evidence per validation run:

- `run_id`
- `run_timestamp`
- `check_id`
- `table_name`
- `severity`
- `failure_count`
- `sample_rows`
- report paths for JSONL and markdown summaries

Core checks:

- required columns exist
- active primary keys are non-null and unique
- foreign keys resolve across patient, study, series, file, event, and observation tables
- path fields are repository-relative
- registry paths resolve
- checksum formats are valid when present
- status values match enums
- provenance fields are populated
- patient events carry a usable time anchor
- lineage edges include source, activity, target, run, and derivation fields

## Lineage Controls

Lineage follows a small W3C PROV-inspired pattern:

- entity: file, table snapshot, cohort manifest, artifact, image, report, model
- activity: ingest, validate, transform, train, evaluate, export
- agent: user, script, workflow, model package

The canonical `lineage_edges` table stays relational and DuckDB-queryable.
Graph infrastructure is unnecessary until relationship queries become a
measured bottleneck.

Every workflow should write a run manifest under
`data/artifacts/index/run_manifests/` and record:

- input files
- input table versions and checksums
- code reference
- parameters
- environment
- outputs
- validation run IDs
- emitted lineage edges

## Monitoring Controls

The local-first monitoring surface is intentionally small:

- ingest freshness by source
- validation failure rate by check and table
- missing file and broken registry path counts
- checksum mismatch and duplicate hash counts
- workflow success/failure counts
- run duration by workflow type
- cohort leakage check results
- subgroup/site/domain performance gaps
- calibration and metric drift for repeated evaluations
- storage growth by archive, tables, and artifacts

Use JSONL logs and markdown summaries first. Add OpenTelemetry only when
multiple scripts or services need correlated traces, metrics, and logs.

## Regulated Mode Boundary

The MVP is not a clinical or medical-device system. If the platform later
supports regulated clinical investigations or clinical decision workflows,
add controls for:

- access review and audit trail review
- change control for validated workflows
- locked dataset snapshots
- reviewer sign-off for validation evidence
- risk assessment and mitigation tracking
- post-deployment model and data monitoring

---

**Up:** [[Home]]
