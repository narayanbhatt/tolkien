---
title: Home
aliases: [home, moc, index]
tags: [meta, moc]
type: moc
---

> **Related:** [[Research/Project Specification]] · [[Architecture/Tolkien Overview]] · [[Workflows/Workflow Index]] · [[Meta/Glossary]]

# genfeat-mri documentation vault

Study-specific **3D brain MRI domain-generalization** research, built on the **Tolkien** platform library. Canonical source docs live in [`docs/`](../); this vault adds navigation, wikilinks, and cross-references.

## Quick paths

| I want to… | Start here |
|------------|------------|
| Understand the research goal | [[Research/Project Specification]] |
| See platform vs MRI app boundary | [[Architecture/Platform vs Application]] |
| Run NIfTI → Zarr ingest | [[Workflows/Demo Ingestion Workflow]] |
| Run a full baseline experiment | [[Workflows/Workflow Index]] |
| Learn Tolkien architecture | [[Architecture/Tolkien Overview]] |
| Look up a term | [[Meta/Glossary]] |
| Find Python modules | [[Meta/Code Index]] |
| Find workflow YAMLs | [[Meta/Config Index]] |
| Understand data layout | [[Meta/Data Layout]] |

## Vault map

```mermaid
flowchart TB
  Home[Home]

  subgraph research [Research]
    Intro[Project Specification]
    Roadmap[Roadmap]
  end

  subgraph architecture [Architecture]
    PlatformApp[Platform vs Application]
    TolkienOverview[Tolkien Overview]
    Primitives[Primitive Object Layer]
    Artifacts[Artifact Layer]
    ControlModel[Control Model]
    ArtifactContract[Artifact Registration Contract]
  end

  subgraph workflows [Workflows]
    WorkflowIndex[Workflow Index]
    DemoIngest[Demo Ingestion Workflow]
    Orchestrate[Orchestrating Experiments]
  end

  subgraph data [Data]
    DbArch[MRI Database Architecture]
    DataLayout[Data Layout]
  end

  subgraph meta [Meta]
    Glossary[Glossary]
    CodeIndex[Code Index]
    ConfigIndex[Config Index]
  end

  subgraph reference [Reference]
    BiomedLandscape[Biomedical Platform Landscape]
  end

  Home --> research
  Home --> architecture
  Home --> workflows
  Home --> data
  Home --> meta
  Home --> reference
```

## All notes

| Section | Notes |
|---------|-------|
| **Research** | [[Research/Project Specification]], [[Research/Roadmap]] |
| **Architecture** | [[Architecture/Platform vs Application]], [[Architecture/Tolkien Overview]], [[Architecture/Primitive Object Layer]], [[Architecture/Artifact Layer]], [[Architecture/Control Model]], [[Architecture/Artifact Registration Contract]] |
| **Workflows** | [[Workflows/Workflow Index]], [[Workflows/Demo Ingestion Workflow]], [[Workflows/Orchestrating Multimodal Experiments]] |
| **Data** | [[Data/MRI Database Architecture]], [[Meta/Data Layout]] |
| **Meta** | [[Meta/Glossary]], [[Meta/Code Index]], [[Meta/Config Index]] |
| **Reference** | [[Reference/Biomedical Platform Landscape]] |

## Platform stack (one glance)

```mermaid
flowchart LR
  subgraph platform [Tolkien platform]
    WF[workflows]
    REG[registry]
    VAL[validation]
    ART[artifacts + primitives + lineage]
  end

  subgraph app [genfeat_mri app]
    ING[NIfTI to Zarr ingest]
    ADP[MRI adapter]
    EXP[experiments]
  end

  subgraph glue [Workspace glue]
    YML[configs/workflows YAML]
  end

  YML --> WF
  YML --> ING
  YML --> ADP
  ING --> ART
  ADP --> REG
```

See [[Architecture/Platform vs Application]] for the hard boundary rule: **Tolkien never imports genfeat_mri**.

---

**Canonical docs:** [`docs/`](../) · **Install:** `pip install -e .` from repo root
