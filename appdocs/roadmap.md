# Multimodal Platform MVP Roadmap

The platform should grow only when local constraints prove the need. The first
goal is reproducible multimodal research, not enterprise-scale infrastructure.

## Phase 0: Contract Freeze

Outputs:

- canonical table contracts for patient, study, series, file, labels, events, observations, and lineage
- CSV mirrors with stable headers
- validation and registry contract files

Exit criteria:

- new tables can be validated from schema contracts
- empty tables are allowed, but headers must match contracts

## Phase 1: MRI Patient-Time Spine

Outputs:

- MRI adapter that emits `patient_events` and `modality_observations`
- acquisition events generated from studies
- imaging observations generated from registered files

Exit criteria:

- every MRI file can be linked to a patient, study, event, and observation
- validation passes or produces explicit blocking failures

## Phase 2: Structured Clinical Adapter

Outputs:

- CSV adapter for clinical observations and outcomes
- relative-time event support for de-identified research datasets
- staging outputs for review before canonical publication

Exit criteria:

- one non-imaging table can be mapped to the same patient-time spine
- identity conflicts are detected before publication

## Phase 3: Reproducible Workflow Runs

Outputs:

- run manifests for each analysis
- lineage edges connecting inputs, activities, agents, and outputs
- artifact registry entries for reports, metrics, model outputs, and cohort manifests

Exit criteria:

- every artifact can be traced to source files, table versions, code reference, and parameters
- validation evidence is linked to workflow outputs

## Phase 4: Evaluation Bundles

Outputs:

- structured evaluation bundle manifests
- cohort definitions and split artifacts
- leakage checks
- metrics with confidence intervals
- subgroup/site/domain performance checks
- calibration summaries where relevant

Exit criteria:

- model results are reproducible without reading notebooks
- domain-generalization claims cite cohort and evaluation artifacts

## Phase 5: Measured Scale-Up

Only add heavier infrastructure when a local bottleneck is observed:

- add containers when environment drift breaks reproducibility
- add OpenTelemetry when logs from multiple workflows need correlation
- add Iceberg when concurrent writes, table snapshots, or partition evolution become painful
- add a graph database only when lineage queries are too slow or too complex for DuckDB
- add a UI only after contracts and workflows stabilize
