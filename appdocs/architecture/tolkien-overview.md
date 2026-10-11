# Tolkien architecture and application flows

**Tolkien** (`tolkien/`) is a domain-agnostic, local-first library for reproducible data workflows. It owns orchestration, registries, validation, lineage, and cohort helpers. Study-specific logic (MRI ingest, adapters, experiments) lives in **`genfeat_mri`** and is composed via workflow YAML or Python — Tolkien never imports the app.

See also:

- [Platform vs application](../platform-vs-app.md) — boundary rules and install layout
- [Demo: ingestion workflow](../demo-ingestion-workflow.md) — end-to-end NIfTI → Zarr walkthrough with sequence diagrams
- [Orchestrating multimodal experiments](../orchestrating-multimodal-experiments-with-tolkien.md) — experiment composition patterns

---

## 1. Package layers

```mermaid
flowchart TB
  subgraph consumers [Composition layer — not inside tolkien]
    yaml[Workflow YAML configs/workflows/]
    app[genfeat_mri application]
    scripts[Custom Python entrypoints]
  end

  subgraph orchestration [Orchestration]
    wf[tolkien.workflows.run_local_workflow<br/>YAML → shell commands + GENFEAT_RUN_ID]
    prov[tolkien.provenance<br/>ProvenanceWorkflowRunner + ProvenancedStep]
  end

  subgraph domain [Domain models]
    art[tolkien.artifacts<br/>Artifact model + register + CsvArtifactWriter]
    prim[tolkien.primitives<br/>Entity Event Observation Relation]
    lin[tolkien.lineage<br/>LineageEdge → lineage_edges.csv]
    adapt[tolkien.adapters<br/>BaseAdapter ClinicalCsvAdapter]
  end

  subgraph registry [Central read/write path]
    dr[DatastoreRegistry]
    reader[MasterTableReader]
    paths[DatastorePaths layout]
    spec[ArtifactPersistSpec]
    rm[run_manifest build/write]
  end

  subgraph quality [Quality and cohorts]
    val[tolkien.validation.validate]
    cohort[tolkien.cohorts.cohort_manifest]
  end

  subgraph storage [On-disk datastore repo_root/data/]
    master[data/master/csv/*.csv]
    payloads[data/artifacts/** payloads]
    manifests[data/artifacts/index/run_manifests/]
    logs[data/logs/validation/]
  end

  yaml --> wf
  scripts --> prov
  app --> dr
  app --> lin

  wf --> rm
  prov --> rm
  prov --> lin

  art --> dr
  prim --> dr
  lin --> dr
  adapt --> master
  spec --> dr

  dr --> paths
  dr --> reader
  reader --> master
  dr --> master
  dr --> payloads
  rm --> manifests
  val --> reader
  val --> logs
  cohort --> reader
  cohort --> manifests
```

---

## 2. On-disk layout

Tolkien writes under a canonical filesystem layout derived from `DatastorePaths`:

```mermaid
flowchart LR
  root[repo_root]

  root --> master[data/master/csv/]
  root --> artifacts[data/artifacts/]
  root --> logs[data/logs/]

  master --> m1[artifacts.csv]
  master --> m2[entities events observations relations.csv]
  master --> m3[patients studies series files.csv]
  master --> m4[lineage_edges.csv]
  master --> m5[patient_events modality_observations.csv]

  artifacts --> a1[index/run_manifests/]
  artifacts --> a2[data/volume_zarr/ ...]
  artifacts --> a3[cohort_manifests/]
  artifacts --> a4[ingestion_reports/]

  logs --> l1[validation/*.jsonl]
```

**`DatastoreRegistry`** is the single entry point for appends to master CSVs, lineage, and run manifests. Callers should prefer it over calling CSV writers directly.

**`MasterTableReader`** (exposed as `registry.reader`) is the single read gateway for master CSV mirrors. Application and platform code should use `reader.read_table(stem)` or `reader.read_active_table(stem)` instead of opening `data/master/csv/*.csv` directly. Every read invokes `DatastorePermissions.assert_can_read` (stubbed no-op today; reserved for future allowlists and audit logging).

---

## 3. Core registry flow

Most catalog writes go through **`DatastoreRegistry`**:

```mermaid
sequenceDiagram
  participant App as Application step<br/>genfeat_mri or CLI
  participant DR as DatastoreRegistry
  participant BA as build_artifact / Artifact model
  participant CW as CsvArtifactWriter
  participant PW as CsvPrimitiveWriter
  participant LE as append_lineage_edges

  App->>DR: persist_artifact(path_rel, spec, writer_fn)
  DR->>DR: resolve_payload_paths + idempotent check
  DR->>App: writer_fn(abs_path) writes bytes
  DR->>BA: build Artifact (+ optional Entity)
  BA->>DR: validate()
  DR->>CW: append_artifacts → artifacts.csv
  DR->>PW: append_primitives → entities/events/...
  DR->>LE: append_lineage_edges → lineage_edges.csv

  App->>DR: append_primitives([Entity, Event, ...])
  DR->>PW: grouped by object_kind → table CSVs

  App->>DR: load_artifact_by_id / by_path_rel
  DR->>App: Artifact.from_csv_row
```

Convenience methods on domain models delegate to the same registry:

- **`Artifact.dump(registry)`** — append artifact row
- **`PrimitiveObject.log(registry)`** — append primitive row(s)
- **`Artifact.load(registry, ...)`** — read back from `artifacts.csv`

---

## 4. Two orchestration modes

Tolkien supports two ways to run pipelines. Use one mode per workflow; do not mix edges between them.

| Mode | Entry | Steps are | Lineage | Manifest |
|------|--------|-----------|---------|----------|
| **YAML / shell** | `tolkien-run-workflow` | Subprocess commands | Written inside each step (e.g. `--lineage`) | `run_local_workflow` |
| **In-process** | Custom Python | `ProvenancedStep` / `WorkflowNode` | Centralized via `ProvenanceSink` after each leaf | `ProvenanceWorkflowRunner` |

### 4a. YAML workflow (default in this repo)

Example: `configs/workflows/nifti_to_subject_zarr.yaml`

```mermaid
flowchart LR
  subgraph config
    wfy[workflow YAML]
    src[source policy YAML]
  end

  subgraph tolkien_orch [tolkien.workflows]
    runner[run_local_workflow]
    runId[GENFEAT_RUN_ID env]
    manifest[run_manifest JSON]
  end

  subgraph step1 [Step 1: ingest]
    ingestCLI[genfeat_mri.ingest.nifti_to_subject_zarr]
    ingest[NiftiToSubjectZarrIngest.run]
  end

  subgraph step2 [Step 2: validate]
    valCLI[tolkien.validation.validate]
  end

  subgraph outputs
    zarr[Zarr stores on disk]
    csv[artifacts entities lineage CSVs]
    vlog[validation reports]
  end

  wfy --> runner
  src --> ingest
  runner --> runId
  runId --> ingestCLI
  ingestCLI --> ingest
  ingest --> zarr
  ingest --> csv
  runner --> valCLI
  valCLI --> vlog
  runner --> manifest
```

Run:

```bash
tolkien-run-workflow configs/workflows/nifti_to_subject_zarr.yaml --repo-root .
# or
python -m tolkien.workflows.run_local_workflow configs/workflows/nifti_to_subject_zarr.yaml --repo-root .
```

### 4b. In-process provenance runner

For Python-native pipelines without a subprocess per step:

```mermaid
flowchart TB
  entry[Python entrypoint]
  ctx[ProvenanceContext<br/>run_id repo_root workflow_name code_ref]
  runner[ProvenanceWorkflowRunner<br/>LIFO stack + retries + checkpoints]
  seq[SequenceStep composite nodes]
  leaf[ProvenancedStep leaves]
  sink[CsvLineageSink → lineage_edges.csv]
  valStep[ValidationProvenanceStep]
  manifest[run_manifest]

  entry --> runner
  ctx --> runner
  runner --> seq
  seq --> leaf
  leaf -->|StepProvenanceRecord.edges| sink
  seq --> valStep
  runner --> manifest
```

Each leaf returns a **`StepProvenanceRecord`**: outcome, used/generated entity refs, and optional **`LineageEdge`** tuples. The runner flushes edges to the sink after each leaf step.

---

## 5. Application flows

### Flow A — Source adapter → master tables

Used by `configs/workflows/mri_patient_time.yaml`: native metadata → canonical CSV rows.

```mermaid
flowchart LR
  src[Source files / master CSVs<br/>patients studies series files]
  adapter[BaseAdapter subclass<br/>e.g. genfeat_mri.adapters.mri_adapter<br/>or tolkien.adapters.clinical_csv_adapter]
  rows[AdapterResult.rows_by_table]
  master[data/master/csv/<br/>patient_events.csv<br/>modality_observations.csv]
  val[tolkien.validation.validate]

  src --> adapter
  adapter --> rows
  rows -->|overwrite_master_csv or write_csv| master
  master --> val
```

Tolkien ships a generic **`ClinicalCsvAdapter`**; MRI-specific mapping lives in **`genfeat_mri.adapters.mri_adapter`**.

### Flow B — Ingest → artifact + entity + lineage

Used by NIfTI → Zarr ingest with `--register --lineage`:

```mermaid
flowchart LR
  files[files.csv + NIfTI paths]
  ingest[genfeat_mri NiftiToSubjectZarrIngest]
  zarr[Zarr payload on disk]
  spec[ArtifactPersistSpec]
  dr[DatastoreRegistry.persist_artifact]
  art[artifacts.csv]
  ent[entities.csv]
  lin[lineage_edges.csv]

  files --> ingest
  ingest --> zarr
  ingest --> spec
  spec --> dr
  dr --> art
  dr --> ent
  dr --> lin
```

### Flow C — Manual artifact registration

CLI: `python -m tolkien.artifacts.register` or **`DatastoreRegistry.write_registered_artifact`**:

```mermaid
flowchart LR
  cli[CLI args / Namespace]
  build[build_artifact]
  art[Artifact + optional Entity]
  dr[DatastoreRegistry]
  csv[artifacts.csv + entities.csv]

  cli --> build --> art --> dr --> csv
```

### Flow D — Cohort selection

`tolkien.cohorts.cohort_manifest` filters active rows from master CSVs by modality and writes a JSON cohort manifest under `data/artifacts/cohort_manifests/`. Downstream ingest can filter on that manifest.

### Flow E — Validation gate

`tolkien.validation.validate` reads schema contracts under `data/master/schema/`, checks master CSVs, and writes JSONL + markdown summaries. Referenced from workflow YAML as a post-step and available as **`ValidationProvenanceStep`** in the in-process runner.

---

## 6. Domain model taxonomy

```mermaid
classDiagram
  class PrimitiveObject {
    +object_kind
    +object_id()
    +validate()
    +as_dict()
    +log(registry)
  }

  class Entity
  class Event
  class Observation
  class Relation

  class Artifact {
    +artifact_id
    +entity_id
    +path_rel / uri
    +dump(registry)
    +load(registry)
  }

  class LineageEdge {
    +source_entity_id
    +target_entity_id
    +derivation_type
    +as_row()
  }

  PrimitiveObject <|-- Entity
  PrimitiveObject <|-- Event
  PrimitiveObject <|-- Observation
  PrimitiveObject <|-- Relation

  DatastoreRegistry --> Artifact : append/load
  DatastoreRegistry --> PrimitiveObject : append
  DatastoreRegistry --> LineageEdge : append
```

| Concept | Role |
|---------|------|
| **Artifacts** | Catalogued files/payloads (Zarr, configs, reports) |
| **Primitives** | Semantic graph nodes (entities, events, observations, relations) |
| **Lineage edges** | PROV-style derivation links between them, keyed by `run_id` |

---

## 7. Platform vs application boundary

```mermaid
flowchart TB
  subgraph tolkien_pkg [tolkien — reusable platform]
    T1[workflows + provenance]
    T2[registry + manifests]
    T3[artifacts + primitives + lineage]
    T4[validation + cohorts]
    T5[generic adapters]
  end

  subgraph genfeat [genfeat_mri — this repo's study app]
    G1[NIfTI → Zarr ingest]
    G2[MRI metadata adapter]
    G3[experiment scripts]
    G4[ApplicationStep.run]
  end

  subgraph glue [Workspace glue — not imported by tolkien]
    YML[configs/workflows/*.yaml]
  end

  YML --> T1
  YML --> G1
  YML --> G2
  G1 --> T3
  G2 --> T5
  G4 -.->|optional| T1
```

**Hard rule:** `tolkien` must not import `genfeat_mri`. Composition happens in YAML or your own Python entrypoints.

---

## 8. Module map

| Module | Responsibility |
|--------|----------------|
| `tolkien.registry` | `DatastoreRegistry`, `MasterTableReader`, `DatastorePaths`, `ArtifactPersistSpec`, read policy stubs, run manifests |
| `tolkien.artifacts` | `Artifact` model, register CLI, CSV writer |
| `tolkien.primitives` | Entity/Event/Observation/Relation dataclasses + CSV writer |
| `tolkien.lineage` | `LineageEdge`, append to `lineage_edges.csv` |
| `tolkien.adapters` | Source-native → canonical table rows |
| `tolkien.workflows` | YAML shell runner (`tolkien-run-workflow`) |
| `tolkien.provenance` | In-process step runner, context, sinks, checkpoints, validation step |
| `tolkien.validation` | Schema-driven CSV validation |
| `tolkien.cohorts` | Cohort manifest builder |

---

## 9. Bundled workflow examples

| Workflow | Steps | Primary outputs |
|----------|-------|-----------------|
| `nifti_to_subject_zarr.yaml` | Ingest → validate | Zarr stores, `artifacts.csv`, `lineage_edges.csv`, validation logs |
| `mri_patient_time.yaml` | MRI adapter → validate | `patient_events.csv`, `modality_observations.csv` |
| `mri_baseline_experiment.yaml` | Experiment registration/finalize | Study-specific artifacts and primitives |

Workflow YAML files may chain Tolkien modules with `genfeat_mri` modules. That composition is workspace glue, not part of Tolkien's public API surface.
