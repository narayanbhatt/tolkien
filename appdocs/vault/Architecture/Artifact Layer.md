---
title: Artifact Layer
aliases:
  - artifacts
  - architecture/artifacts
tags:
  - architecture
  - platform
  - artifacts
source: docs/architecture/artifacts.md
type: spec
---

> **Related:**
- [[Architecture/Primitive Object Layer]]
- [[Architecture/Artifact Registration Contract]]
- [[Meta/Data Layout]]
- [[Home]]

# Artifact Layer

Artifacts are specialized primitive `Entity` objects for stored, versioned, and
reproducible platform objects. Keep top-level artifact types few; use role,
format, schema, metadata, observations, and relations for specificity.

## Artifact Versus Observation

- Artifact: stored object, bundle, file, model, config, report, visual, or
  environment description.
- Observation: queryable claim, value, metric, label, or reference derived from
  or pointing to artifacts.

Example:

- A segmentation mask is a `data_artifact`.
- Tumor volume derived from that mask is an `Observation`.
- The observation can be linked to the artifact with `Relation(type=derived_from)`.

## Artifact Types

### `data_artifact`

Computational data consumed by downstream steps.

Examples: segmentation masks, feature tables, embeddings, computed output
tables, cleaned clinical tables, waveform window exports, and variant tables.

### `model_artifact`

Learned or executable model objects.

Examples: checkpoints, weights, tokenizers, calibrators, and ensemble
definitions.

### `configuration_artifact`

Reusable instructions or rules used by runs.

Examples: preprocessing configs, training configs, evaluation configs, cohort
definitions, adapter/source configs, validation rulesets, deployment configs,
and hyperparameter search spaces.

This is the broad reducer for config-like artifacts. Do not create separate
artifact types for config roles unless the lifecycle truly differs.

### `report_artifact`

Human-readable or semi-structured explanation.

Examples: validation summaries, model cards, data cards, cohort reports,
quality-control reports, domain-shift reports, and evaluation reports.

### `visual_artifact`

Rendered visual output.

Examples: MRI slices, segmentation overlays, training curves, confusion
matrices, calibration plots, embedding plots, and architecture diagrams.

### `environment_artifact`

Reproducibility context for computation.

Examples: requirements files, lockfiles, Dockerfiles, container digests, conda
environments, git patches, hardware summaries, and runtime manifests.

### `collection_artifact`

A manifest or bundle whose primary role is grouping other artifacts.

Examples: evaluation bundles, model releases, dataset releases, cohort packages,
experiment packages, deployment packages, and multimodal case bundles.

Collection membership is represented through primitive `Relation(type=contains)`
from the collection artifact entity to member artifact entities.

## Contract Fields

Artifacts are stored in `data/master/csv/artifacts.csv` with:

```text
artifact_id
entity_id
artifact_type
artifact_role
path_rel
uri
media_type
format
schema_ref
sha256
byte_size
created_by_event_id
created_by_run_id
version
status
metadata_json
source_name
source_version
ingested_at
record_version
is_active
```

Field semantics:

- `artifact_type`: broad lifecycle category.
- `artifact_role`: specific purpose.
- `path_rel` / `uri`: where the payload or manifest lives.
- `media_type` / `format`: physical representation.
- `schema_ref`: how to interpret contents.
- `created_by_event_id` / `created_by_run_id`: provenance anchors.
- `entity_id`: backing primitive entity with `entity_type=artifact`.

## On-Disk Layout

The folder tree is for human organization. Registry rows are the source of
truth.

```text
data/artifacts/
  data/
  models/
  configs/
  reports/
  visuals/
  environments/
  collections/
  index/
```

## Multimodal Examples

- MRI segmentation mask: `artifact_type=data_artifact`,
  `artifact_role=segmentation_mask`, `format=nifti`.
- Radiomics features: `artifact_type=data_artifact`,
  `artifact_role=feature_table`, `format=parquet`.
- Clinical cleaned table: `artifact_type=data_artifact`,
  `artifact_role=cleaned_clinical_table`, `format=parquet`.
- Waveform export: `artifact_type=data_artifact`,
  `artifact_role=waveform_window_export`, `format=wfdb`.
- Variant table: `artifact_type=data_artifact`,
  `artifact_role=variant_table`, `format=vcf`.
- Training config: `artifact_type=configuration_artifact`,
  `artifact_role=training_config`, `format=yaml`.
- Validation ruleset: `artifact_type=configuration_artifact`,
  `artifact_role=validation_config`, `format=yaml`.
- Model card: `artifact_type=report_artifact`,
  `artifact_role=model_card`, `format=markdown`.
- Evaluation bundle: `artifact_type=collection_artifact`,
  `artifact_role=evaluation_bundle`, `format=json`.

## Collection Rule

`collection_artifact` is the collection signal.

Rules:

- Non-collection artifact types are atomic by default.
- Collection artifacts point to a manifest through `path_rel` or `uri`.
- Members are linked with primitive `Relation(type=contains)`.
- Collections may contain other collections, but cycle detection should be added
  only when nested collection use becomes real.

---

**Up:** [[Home]]
