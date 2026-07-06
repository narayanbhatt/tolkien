# Local Workflows

This package provides a **small, dependency-light workflow runner** for local reproducibility: parse a YAML list of shell commands, run them with a shared `GENFEAT_RUN_ID`, and write a run manifest.

The runner is **agnostic** to what those commands are. A **downstream application** in another package may contribute steps (ingest, study-specific tools); Tolkien does not reference any particular application.

Workflow code should:

- keep the runner generic (no imports from study packages)
- rely on manifests under `data/artifacts/index/run_manifests/` when used in this workspace
- avoid external orchestration until needed

## Running

Install the workspace (or any environment that provides `tolkien`), then:

```bash
tolkien-run-workflow path/to/workflow.yaml --repo-root .
# or
python -m tolkien.workflows.run_local_workflow path/to/workflow.yaml --repo-root .
```

YAML files in this repository may call **application** modules (e.g. separate Python packages) alongside Tolkien modules—that is repository glue, not Tolkien’s public API surface.
