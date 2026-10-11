---
title: Code Index
aliases: [code-index, modules]
tags: [meta, code, platform, genfeat-mri]
type: index
---

> **Related:** [[Architecture/Tolkien Overview#8. Module map]] · [[Architecture/Platform vs Application]] · [[Workflows/Demo Ingestion Workflow]] · [[Home]]

# Code Index

Repository modules referenced across the vault. Paths are relative to the repo root — click to open from Obsidian.

## Tolkien platform (`tolkien/`)

### Orchestration

| Module | Role | Path |
|--------|------|------|
| `run_local_workflow` | YAML → shell commands + GENFEAT_RUN_ID | [`tolkien/workflows/run_local_workflow.py`](../../../tolkien/workflows/run_local_workflow.py) |
| `ProvenanceWorkflowRunner` | In-process step runner | `tolkien/provenance/runner.py` |
| `cohort_manifest` | Cohort JSON from master CSVs | `tolkien/cohorts/cohort_manifest.py` |

### Registry & manifests

| Module | Role | Path |
|--------|------|------|
| `DatastoreRegistry` | Central write path for CSVs, lineage, manifests | `tolkien/registry/datastore.py` |
| `MasterTableReader` | Central read path for master CSVs | `tolkien/registry/reader.py` |
| `run_manifest` | build_manifest / write_manifest | [`tolkien/registry/run_manifest.py`](../../../tolkien/registry/run_manifest.py) |

### Domain models

| Module | Role | Path |
|--------|------|------|
| `tolkien.artifacts` | Artifact model, register, CSV writer | [`tolkien/artifacts/register.py`](../../../tolkien/artifacts/register.py) |
| `tolkien.primitives` | Entity, Event, Observation, Relation | `tolkien/primitives/models.py` |
| `tolkien.lineage` | LineageEdge → lineage_edges.csv | `tolkien/lineage/edges.py` |
| `tolkien.validation` | Schema-driven CSV validation CLI | `tolkien/validation/validate.py` |
| `tolkien.adapters` | BaseAdapter, ClinicalCsvAdapter | `tolkien/adapters/base.py` |

## genfeat_mri application (`apps/genfeat_mri/`)

| Module | Role | Path |
|--------|------|------|
| `NiftiToSubjectZarrIngest` | NIfTI → subject Zarr ingest | [`nifti_to_subject_zarr.py`](../../../apps/genfeat_mri/genfeat_mri/ingest/nifti_to_subject_zarr.py) |
| `MriAdapter` | MRI metadata → patient-time tables | [`mri_adapter.py`](../../../apps/genfeat_mri/genfeat_mri/adapters/mri_adapter.py) |
| `from_mri_scaffold` | Imaging scaffold → primitives | [`from_mri_scaffold.py`](../../../apps/genfeat_mri/genfeat_mri/primitives/from_mri_scaffold.py) |
| `ApplicationStep` | Step contract ABC | [`base.py`](../../../apps/genfeat_mri/genfeat_mri/steps/base.py) |
| `register_assets` | Baseline experiment asset registration | [`register_assets.py`](../../../apps/genfeat_mri/genfeat_mri/experiments/register_assets.py) |
| `mri_baseline_finalize` | Cohort stats + evaluation bundle | [`mri_baseline_finalize.py`](../../../apps/genfeat_mri/genfeat_mri/experiments/mri_baseline_finalize.py) |
| `mri_dataset` | MRIDataset / Zarr channel views for modeling | [`mri_dataset.py`](../../../apps/genfeat_mri/genfeat_mri/experiments/mri_dataset.py) |
| `load` | Zarr open/read helpers | [`load.py`](../../../apps/genfeat_mri/genfeat_mri/load/load.py) |
| `lookup` | Master table join helpers | [`lookup.py`](../../../apps/genfeat_mri/genfeat_mri/load/lookup.py) |
| `event_artifacts` | Event → artifact resolution | [`event_artifacts.py`](../../../apps/genfeat_mri/genfeat_mri/load/event_artifacts.py) |

## Call-site map (artifact registration)

Used by [[Architecture/Artifact Registration Contract]]:

- [`nifti_to_subject_zarr.py`](../../../apps/genfeat_mri/genfeat_mri/ingest/nifti_to_subject_zarr.py) — Zarr register + lineage
- [`register_assets.py`](../../../apps/genfeat_mri/genfeat_mri/experiments/register_assets.py) — experiment config artifacts
- [`mri_baseline_finalize.py`](../../../apps/genfeat_mri/genfeat_mri/experiments/mri_baseline_finalize.py) — bundle + collection registration

## Entry points

```bash
tolkien-run-workflow configs/workflows/nifti_to_subject_zarr.yaml --repo-root .
python -m genfeat_mri.ingest.nifti_to_subject_zarr --repo-root . --config configs/sources/zarr_ingest_brats.yaml --write --register --lineage
python -m genfeat_mri.adapters.mri_adapter --repo-root . --source-name local_mri_exploration --source-version v1 --write
python -m tolkien.validation.validate --repo-root . --run-id val_post_zarr_ingest
```

See [[Meta/Config Index]] for workflow YAML paths.

---

**Up:** [[Home]]
