---
title: MRI Database Architecture
aliases:
  - mri-database-architecture
  - database-architecture
tags:
  - data
  - genfeat-mri
  - architecture
source: docs/mri-domain-generalization-database-architecture.md
type: spec
---

> **Related:**
- [[Meta/Data Layout]]
- [[Research/Project Specification]]
- [[Architecture/Tolkien Overview]]
- [[Home]]

# 3D Brain MRI Platform Database Architecture (Domain Generalization)

## 1) Recommended Architecture

- Keep `data/archive` as immutable source-of-truth for raw NIfTI (`.nii/.nii.gz`) and never rewrite files in place; track `sha256`, byte size, and ingest timestamp in `files`.
- Convert canonical CSVs in `data/master/csv` into canonical Parquet tables in `data/master/parquet` (same logical schema, typed columns, constraints enforced in ETL).
- Use DuckDB as the default query engine (`catalog.duckdb`) with views over Parquet for fast local joins and modality/site/domain slicing.
- Keep registries (`analysis_registry`, `artifact_registry`, `image_registry`) append-only and event-like; each row references immutable upstream entities plus run/artifact hashes.
- Store derived tabular indexes in Parquet under `data/indexes/parquet`; use row-group statistics-friendly sort order (`site`, `modality`, `study_date`, `series_uid`) for pruning.
- For high-dimensional derived tensors/features (not raw archive), use Zarr with chunking aligned to access pattern (for example per-volume or per-slab), and sharding to avoid tiny-file explosion.
- Introduce one internal lineage spine: `run_id` + `artifact_id` + `image_id` joins all processing outputs to source `file_id`.
- Keep pseudonym-only identifiers in all tables; PHI mapping remains external and never materialized in analytics storage.
- Emit telemetry via OpenTelemetry collector: traces for pipelines, metrics for throughput/latency/quality, logs for row-level ingest/validation failures.
- Use one migration trigger: when concurrent writers, reproducible snapshots, and partition evolution become pain points, move Parquet datasets into Iceberg tables (same files, stronger table semantics).

## 2) Schema

### Core Entity Tables

#### `patients`
- Key columns: `patient_id` (pseudonym), `sex`, `birth_year_bin`, `site_id`, `created_at`
- Primary key: `patient_id`
- Foreign keys: `site_id -> sites.site_id` (optional dimension)

#### `studies`
- Key columns: `study_id`, `patient_id`, `study_instance_uid`, `study_date`, `accession_pseudo`
- Primary key: `study_id`
- Foreign keys: `patient_id -> patients.patient_id`
- Unique: `study_instance_uid`

#### `series`
- Key columns: `series_id`, `study_id`, `series_instance_uid`, `modality`, `sequence_name`, `site_id`
- Primary key: `series_id`
- Foreign keys: `study_id -> studies.study_id`
- Unique: `series_instance_uid`

#### `files`
- Key columns: `file_id`, `series_id`, `relative_path`, `format`, `sha256`, `bytes`, `voxel_shape`, `spacing_xyz`, `orientation`
- Primary key: `file_id`
- Foreign keys: `series_id -> series.series_id`
- Unique: `sha256` (recommended), `relative_path` (within archive root)

### Outcome And Label Tables

#### `labels_outcomes`
- Key columns: `label_id`, `file_id` (or `study_id` based on label granularity), `task_name`, `label_value`, `label_source`, `label_version`
- Primary key: `label_id`
- Foreign keys: `file_id -> files.file_id` (nullable if study-level), `study_id -> studies.study_id` (nullable if file-level)

### Identity Bridge

#### `id_crosswalk`
- Key columns: `crosswalk_id`, `source_system`, `source_entity_type`, `source_id`, `patient_id|study_id|series_id|file_id`
- Primary key: `crosswalk_id`
- Foreign keys: one canonical entity ID by type
- Unique: `(source_system, source_entity_type, source_id)`

### Registries And Lineage

#### `image_registry`
- Key columns: `image_id`, `file_id`, `image_role` (`raw|preprocessed|resampled`), `created_by_run_id`, `image_hash`
- Primary key: `image_id`
- Foreign keys: `file_id -> files.file_id`, `created_by_run_id -> analysis_registry.run_id`

#### `artifact_registry`
- Key columns: `artifact_id`, `run_id`, `artifact_type` (`model|feature|report|mask`), `uri`, `sha256`, `parent_artifact_id`
- Primary key: `artifact_id`
- Foreign keys: `run_id -> analysis_registry.run_id`, `parent_artifact_id -> artifact_registry.artifact_id`

#### `analysis_registry`
- Key columns: `run_id`, `pipeline_name`, `pipeline_version`, `git_commit`, `params_json`, `status`, `started_at`, `ended_at`
- Primary key: `run_id`

#### `lineage_edges`
- Key columns: `edge_id`, `run_id`, `input_type`, `input_id`, `output_type`, `output_id`
- Primary key: `edge_id`
- Foreign keys: `run_id -> analysis_registry.run_id`
- Purpose: explicit many-to-many lineage across image/artifact/analysis objects

## 3) Storage Format Matrix

| Data Type | Format | Why | Read/Write Pattern |
|---|---|---|---|
| Raw MRI volumes (`data/archive`) | NIfTI (`.nii/.nii.gz`) on immutable filesystem/object store | Standard neuroimaging exchange format; preserves fidelity and interoperability | Write once at ingest, read in large sequential chunks |
| Canonical metadata tables | Parquet | Columnar + compression + efficient column pruning for analytics joins | Append/overwrite by partition; frequent selective reads |
| Registries (`analysis/artifact/image`) | Parquet (append-only) | Typed, compact, queryable history; easy DuckDB/Spark interoperability | High-frequency appends, lineage/audit reads |
| Derived tabular indexes | Parquet (partitioned) | Fast filtered scans, cheap recomputation, SQL-native | Periodic batch writes, high-frequency filtered reads |
| High-dimensional derived arrays/features | Zarr (+ sharding) | Chunking/sharding aligns to access patterns and reduces small-file overhead | Chunk-level random reads, batched writes |
| Operational logs | JSON Lines locally + OTLP export | Simple local debugging and standards-based telemetry pipeline | Continuous append, search by `run_id`/`file_id` |
| Metrics/traces | OpenTelemetry (OTLP) backend | Unified traces/metrics/logs model with vendor-neutral instrumentation | Continuous ingest, dashboard and alert queries |
| Table abstraction at scale | Iceberg over Parquet | Schema/partition evolution + snapshot/time-travel + atomic commits | Concurrent writers/readers and reproducible snapshot reads |

## 4) Observability Checklist

- Ingest throughput: files/hour and bytes/hour by `site_id`, `modality`
- Ingest latency p50/p95 from discovery to canonical commit
- Validation failure rate by table and rule (null key, bad UID, bad modality enum)
- Referential integrity error count (`series.study_id`, `files.series_id`, etc.)
- Duplicate-content detection (`sha256`) expected vs unexpected repeats
- Raw-to-canonical reconciliation mismatches between archive and `files`
- Partition skew metric (rows per partition; hot/cold partition detection)
- Query performance SLO p95 for core joins and modality filters
- Pipeline run success rate by `pipeline_name` and `pipeline_version`
- Run duration p50/p95 with failure-stage distribution
- Lineage completeness: percentage of outputs with valid upstream `run_id` and source IDs
- Artifact integrity: percentage with valid checksum and resolvable URI
- Label drift checks: class distribution shift by site and time window
- Domain-generalization diagnostics: per-site performance deltas and worst-site gap
- Telemetry pipeline health: dropped spans/metrics/logs rate
- Alerting rules: ingest halted, validation spike, failed-run spike, latency breach
- Data freshness SLA: max age of latest successful ingest per source
- Storage growth monitor: archive vs parquet vs artifacts with 30/90-day forecast

## 5) Phased Rollout

### Day 0
- Freeze current CSV schema and define canonical column types plus PK/FK contract
- Build deterministic CSV-to-Parquet ETL for `patients`, `studies`, `series`, `files`, `labels_outcomes`, and `id_crosswalk`
- Create DuckDB catalog and stable views (`v_patient_study_series_file`, `v_modality_site_index`)
- Add append-only registry writes with mandatory `run_id`, `artifact_id`, and checksum
- Add baseline observability (pipeline traces, ingest/query metrics, validation logs)

### Day 30
- Partition Parquet by `site_id`, `modality`, `study_year` (coarse, high-selectivity keys)
- Add `lineage_edges` and enforce run/artifact/image linkage checks in data quality jobs
- Introduce Zarr for derived high-dimensional outputs that need chunk-random access
- Add automated quality gates (FK integrity, duplicate hash policy, label sanity checks)
- Publish core dashboards and alert rules for ingest, quality, and pipeline reliability

### Day 90
- Promote to Iceberg if thresholds are met: concurrent writers, recurring backfills, snapshot reproducibility, partition redesign pressure
- Move canonical, registry, and index tables under Iceberg while keeping raw archive immutable
- Add snapshot-based experiment reproducibility (`run_id` references table snapshot IDs)
- Add formal SLOs and on-call alerts for freshness, run success, and query latency

## 6) Risks and Mitigations

1. **Schema drift during CSV-to-Parquet transition**  
   Mitigation: versioned schema registry + contract tests on each ETL run.

2. **Over-partitioning for small/medium datasets**  
   Mitigation: start coarse (`site`, `modality`, `year`) and refine only with telemetry evidence.

3. **Small-file explosion in derived arrays**  
   Mitigation: use Zarr sharding and chunk sizing based on observed access traces.

4. **Incomplete lineage breaks reproducibility**  
   Mitigation: make `run_id` mandatory for every derived image/artifact write; block publish if lineage edges are missing.

5. **Premature lakehouse complexity**  
   Mitigation: keep DuckDB + Parquet until explicit scale/concurrency triggers, then migrate incrementally to Iceberg.

---

**Up:** [[Home]]
