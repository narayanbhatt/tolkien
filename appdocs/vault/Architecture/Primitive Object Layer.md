---
title: Primitive Object Layer
aliases:
  - primitives
  - architecture/primitives
tags:
  - architecture
  - platform
  - primitives
source: docs/architecture/primitives.md
type: spec
---

> **Related:**
- [[Architecture/Artifact Layer]]
- [[Architecture/Tolkien Overview]]
- [[Meta/Glossary]]
- [[Home]]

# Primitive Object Layer

The platform starts with four first-class primitives. Specialized biomedical
objects should inherit from these ideas instead of creating new foundations.

## Primitives

### Entity

An `Entity` is an identifiable thing.

Examples:

- patient
- study
- series
- MRI volume
- artifact
- model
- cohort
- dataset

Use entities for objects that need stable identity, lifecycle, versioning, and
relations to other objects.

### Event

An `Event` is a time-anchored occurrence.

Examples:

- MRI acquisition
- diagnosis
- intervention
- ingest run
- validation run
- model training run

Events carry absolute or relative time. For de-identified research datasets,
relative anchors such as `baseline` and offsets in days are preferred over
calendar dates.

### Observation

An `Observation` is a queryable fact, measurement, assertion, label, metric, or
reference.

Examples:

- `mri.modality = t1ce`
- `storage.byte_size = 17856352`
- `clinical.tumor_grade = HGG`
- `metrics.auc = 0.84`
- `mri.t1ce_volume = ent_fil_123`

Observations should stay small and queryable. Do not store large binary arrays
or full 3D volumes inside observation rows.

### Relation

A `Relation` is a typed link between primitive objects.

Examples:

- patient `has_study` study
- study `contains` MRI volume
- acquisition event `generated` MRI volume
- artifact `derived_from` file
- cohort `includes` patient

Relations carry membership, hierarchy, containment, and provenance without
requiring a graph database.

## Abstract Classes

The implementation uses one shallow abstract layer:

```text
PrimitiveObject
  EntityBase
  EventBase
  ObservationBase
  RelationBase
```

Each concrete object exposes:

- `object_id()`
- `validate()`
- `as_dict()`

`as_dict()` returns a storage-neutral primitive record. It is not a CSV/Parquet
method. Writers are responsible for flattening records into storage formats.

## Serialization Boundary

```text
PrimitiveObject -> as_dict() -> PrimitiveRecord
PrimitiveRecord -> CsvPrimitiveWriter -> CSV row
```

This keeps primitive classes independent of storage details. The MVP implements
CSV writing only; Parquet can be added later without changing primitive objects.

## MRI Volume Rule

A 3D MRI volume is an entity:

```text
Entity(entity_type = mri_volume)
```

Observations describe or reference that entity:

```text
Observation(code_system = mri, code = modality, value_text = t1ce)
Observation(code_system = storage, code = path_rel, value_text = data/archive/...)
Observation(code_system = mri, code = t1ce_volume, value_type = entity_ref, value_text = ent_fil_...)
```

The volume bytes remain in a native file/object location. The observation table
contains queryable facts or references, not the 3D array itself.

## Specialization Rules

- Specializations may add constraints, helper constructors, or domain-specific
  validation.
- Specializations must not remove base fields.
- Query-critical facts should remain in observation columns, not only metadata.
- Large native data should remain entities/files/artifacts and be referenced by
  observations or relations.
- Relations should represent structure and provenance rather than hidden object
  references inside metadata.

---

**Up:** [[Home]]
