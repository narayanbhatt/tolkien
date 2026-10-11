# Platform vs application

**Tolkien** (`tolkien`, repository directory `tolkien/`) and the genfeat-mri study are independent concerns.

For package layers, on-disk layout, registry flows, and orchestration diagrams, see [architecture/tolkien-overview.md](architecture/tolkien-overview.md).

- **Tolkien** is the **domain-agnostic** platform library: workflows runner, manifests, validation, artifacts, primitives, cohorts, lineage. It must **never** import `genfeat_mri` or encode MRI, neuroimaging, or experiment-specific logic.
- This **repository** is a **workspace** that happens to **host** Tolkien **and** a separate study application (`genfeat_mri`). Shipping both in one tree does not make them one product—Tolkien is reusable without the MRI app.

## Tolkien — Python package `tolkien` (directory `tolkien/`)

- Workflow runner: `tolkien.workflows.run_local_workflow`
- Run manifests: `tolkien.registry.run_manifest`
- Master-table reads: `tolkien.registry.MasterTableReader` (via `DatastoreRegistry.reader`)
- Validation: `tolkien.validation.validate`
- Artifact and primitive **framework**: `tolkien.artifacts`, `tolkien.primitives`
- Cohorts: `tolkien.cohorts`
- Lineage: `tolkien.lineage`
- Generic adapters: `tolkien.adapters.base`, `clinical_csv_adapter`, and reusable table column lists in `patient_time_fields` (not MRI-specific—any multimodal patient-time pipeline can use the same shapes)

**Hard rule:** `tolkien` must not import `genfeat_mri`.

**Read/write split:** Tolkien owns writes through `DatastoreRegistry` and reads through `MasterTableReader` (`registry.reader`). Study-specific lookup helpers (e.g. event → artifact resolution) stay in `genfeat_mri/load/` but must call the reader, not open master CSV paths directly.

## `genfeat_mri` (Python package; directory `apps/genfeat_mri/genfeat_mri/`)

**Study / experiment application** for this repo only: MRI ingest, MRI metadata adapter, experiment scripts, study-specific primitive mappers (e.g. `primitives/from_mri_scaffold.py`), and `ApplicationStep` implementations.

Workflow YAMLs under `configs/workflows/` are **glue for this workspace**: they may chain `tolkien` steps with `genfeat_mri` steps. That composition lives in **config**, not inside the `tolkien` package.

## Install

From the repository root (workspace):

```bash
pip install -e .
```

This installs **both** packages. To use **only** Tolkien in another project, depend on `tolkien` (e.g. copy or publish that tree) and do not add `genfeat_mri`.

Entry point `tolkien-run-workflow` runs the **Tolkien** workflow runner; YAML files decide whether any **application** modules are invoked.
