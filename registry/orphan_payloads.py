"""Heuristic scan for Zarr payloads under ``data/artifacts`` without ``artifacts.csv`` rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def registered_path_rel_set(repo_root: Path) -> set[str]:
    """
    Active ``artifacts.csv`` path_rel values, POSIX-normalized.

    Args:
            repo_root (Path): Repository root; relative paths resolve against this directory.

    Returns:
            Set of active, POSIX-normalized ``path_rel`` values from ``artifacts.csv``.
    """

    from tolkien.registry.datastore_registry import DatastoreRegistry

    registry = DatastoreRegistry(repo_root.resolve())
    out: set[str] = set()
    for row in registry.read_master_csv_rows("artifacts"):
        pr = row.get("path_rel", "").strip().replace("\\", "/")
        if pr and str(row.get("is_active", "True")).lower() != "false":
            out.add(pr)
    return out


def orphan_zarr_dirs(repo_root: Path) -> list[str]:
    """
    List ``*.zarr`` directories under ``data/artifacts`` not registered in ``artifacts.csv``.

    Args:
            repo_root (Path): Repository root; relative paths resolve against this directory.

    Returns:
            Sorted repository-relative paths to unregistered ``*.zarr`` directories.
    """

    base = repo_root.resolve() / "data" / "artifacts"
    if not base.is_dir():
        return []
    reg = registered_path_rel_set(repo_root)
    root = repo_root.resolve()
    orphans: list[str] = []
    for p in base.rglob("*.zarr"):
        if not p.is_dir():
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if rel not in reg:
            orphans.append(rel)
    orphans.sort()
    return orphans


def main() -> None:
    """
    CLI: report Zarr payload paths missing from the artifact registry.
    
    Returns:
    None.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    orphans = orphan_zarr_dirs(repo_root)
    print(json.dumps({"orphan_zarr_count": len(orphans), "orphans": orphans}, indent=2))


if __name__ == "__main__":
    main()
