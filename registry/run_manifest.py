"""Run manifest writer for local-first reproducible workflows."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tolkien._util.crypto import sha256_file
from tolkien._util.time import utc_now
from tolkien.registry.layout import DatastorePaths


def git_commit(repo_root: Path) -> str:
    """
    Return ``git rev-parse HEAD`` for ``repo_root``, or ``unknown`` on failure.

    Args:
            repo_root (Path): Repository root; relative paths resolve against this directory.

    Returns:
            Current ``git rev-parse HEAD`` for ``repo_root``, or ``unknown``.
    """

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def table_versions(paths: DatastorePaths) -> dict[str, dict[str, Any]]:
    """
    Fingerprint every master CSV (path, size, mtime, sha256) for reproducibility.

    Args:
            paths (DatastorePaths): Canonical :class:`~tolkien.registry.layout.DatastorePaths` for the workspace.

    Returns:
            Per-table fingerprint dict keyed by CSV stem.
    """

    versions: dict[str, dict[str, Any]] = {}
    for path in sorted(paths.master_csv.glob("*.csv")):
        stat = path.stat()
        versions[path.stem] = {
            "path": str(path.relative_to(paths.repo_root)),
            "bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "sha256": sha256_file(path),
        }
    return versions


def build_manifest(
    *,
    paths: DatastorePaths,
    run_type: str,
    status: str,
    parameters: dict[str, Any] | None = None,
    input_files: list[str] | None = None,
    outputs: list[str] | None = None,
    validation_run_ids: list[str] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Assemble a run manifest payload for audit and reproducibility.

    Args:
            paths (DatastorePaths): Canonical :class:`~tolkien.registry.layout.DatastorePaths` for the workspace. Keyword-only.
            run_type (str): Workflow category string stored as ``run_type`` in the manifest. Keyword-only.
            status (str): Terminal run status (for example ``completed`` or ``failed``). Keyword-only.
            parameters (dict[str, Any] | None): JSON-serializable parameters recorded in the run manifest. Keyword-only.
            input_files (list[str] | None): Input file paths listed in the run manifest. Keyword-only.
            outputs (list[str] | None): Output paths declared or discovered for the run manifest. Keyword-only.
            validation_run_ids (list[str] | None): Validation gate run IDs associated with this workflow run. Keyword-only.
            run_id (str | None): Workflow run identifier (often ``GENFEAT_RUN_ID``). Keyword-only.

    Returns:
            Run manifest mapping.
    """

    resolved_run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
    now = utc_now()
    return {
        "run_id": resolved_run_id,
        "run_type": run_type,
        "started_at": now,
        "completed_at": now,
        "status": status,
        "code_ref": git_commit(paths.repo_root),
        "parameters": parameters or {},
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cwd": os.getcwd(),
        },
        "input_files": input_files or [],
        "input_tables": table_versions(paths),
        "outputs": outputs or [],
        "validation": {
            "validation_run_ids": validation_run_ids or [],
            "status": "not_run" if not validation_run_ids else "recorded",
        },
        "lineage_edges": [],
    }


def write_manifest(paths: DatastorePaths, manifest: dict[str, Any]) -> Path:
    """
    Write manifest JSON to ``run_manifests/{run_id}.json``.

    Args:
            paths (DatastorePaths): Canonical :class:`~tolkien.registry.layout.DatastorePaths` for the workspace.
            manifest (dict[str, Any]): Run manifest mapping written as JSON under ``run_manifests/``.

    Returns:
            Path to written ``run_manifests/{run_id}.json``.
    """

    output_root = paths.run_manifests_dir
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / f"{manifest['run_id']}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def main() -> None:
    """
    CLI: create and write a standalone run manifest.
    
    Returns:
    None.
    """

    parser = argparse.ArgumentParser(description="Create a local workflow run manifest.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-type", default="manual")
    parser.add_argument("--status", default="completed")
    parser.add_argument("--parameters-json", default="{}")
    parser.add_argument("--input-file", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--validation-run-id", action="append", default=[])
    args = parser.parse_args()

    paths = DatastorePaths(args.repo_root.resolve())
    manifest = build_manifest(
        paths=paths,
        run_type=args.run_type,
        status=args.status,
        parameters=json.loads(args.parameters_json),
        input_files=args.input_file,
        outputs=args.output,
        validation_run_ids=args.validation_run_id,
    )
    path = write_manifest(paths, manifest)
    print(json.dumps({"run_id": manifest["run_id"], "manifest_path": str(path)}, indent=2))


if __name__ == "__main__":
    main()
