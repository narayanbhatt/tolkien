# Tolkien (`tolkien`)

**Codename Tolkien** — a **domain-agnostic** local-first library for reproducible data workflows: a minimal workflow runner, run manifests, validation hooks, artifact and primitive registries, cohort manifests, and lineage helpers. The importable package name is `tolkien`.

- **No dependency on any study or modality.** Nothing here imports `genfeat_mri` or assumes MRI, neuroimaging, or this repository’s datasets.
- **Consumer applications** (such as `genfeat_mri` in this workspace) layer their own ingest, adapters, and experiment steps on top and invoke Tolkien via `python -m tolkien...`.

See the repository’s [appdocs/platform-vs-app.md](appdocs/platform-vs-app.md) for how this package relates to optional application packages shipped beside it.

For architecture diagrams and end-to-end application flows, see [appdocs/architecture/tolkien-overview.md](appdocs/architecture/tolkien-overview.md).
