"""Create simple cohort manifests from canonical CSV metadata."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from tolkien._util.time import utc_now
from tolkien.registry import DatastoreRegistry, is_active_row
from tolkien.registry.run_manifest import table_versions


def main() -> None:
    """
    CLI: build a modality-filtered cohort manifest JSON from master CSVs.
    
    Returns:
    None.
    """

    parser = argparse.ArgumentParser(description="Build a simple modality-filtered cohort manifest.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--cohort-name", default="default")
    parser.add_argument("--cohort-manifest-id", default="", help="Stable ID (e.g. cohort_baseline_v1); default random uuid.")
    parser.add_argument("--modality", default="")
    parser.add_argument("--output-dir", type=Path, default=None, help="Override default cohort_manifests dir.")
    args = parser.parse_args()

    registry = DatastoreRegistry(args.repo_root.resolve())
    reader = registry.reader
    patients = reader.read_table("patients")
    studies = reader.read_table("studies")
    series = reader.read_table("series")
    files = reader.read_table("files")

    selected_files = [
        row for row in files
        if is_active_row(row)
        and (not args.modality or row.get("modality") == args.modality)
    ]
    selected_series = {row["series_uid"] for row in selected_files}
    selected_study_ids = {
        row["study_uid"]
        for row in series
        if is_active_row(row) and row.get("series_uid") in selected_series
    }
    selected_patient_ids = {
        row["patient_uid"]
        for row in studies
        if is_active_row(row) and row.get("study_uid") in selected_study_ids
    }
    active_patient_ids = {row["patient_uid"] for row in patients if is_active_row(row)}
    selected_patient_ids = selected_patient_ids.intersection(active_patient_ids)

    cohort_id = (args.cohort_manifest_id or "").strip() or f"cohort_{uuid.uuid4().hex[:12]}"
    manifest = {
        "cohort_manifest_id": cohort_id,
        "cohort_name": args.cohort_name,
        "created_at": utc_now(),
        "criteria": {
            "modality": args.modality or "any",
            "active_records_only": True,
        },
        "counts": {
            "patients": len(selected_patient_ids),
            "studies": len(selected_study_ids),
            "series": len(selected_series),
            "files": len(selected_files),
        },
        "ids": {
            "patient_uid": sorted(selected_patient_ids),
            "study_uid": sorted(selected_study_ids),
            "series_uid": sorted(selected_series),
            "file_uid": sorted(row["file_uid"] for row in selected_files),
        },
        "input_table_versions": table_versions(registry.paths),
    }

    output_dir = args.output_dir if args.output_dir is not None else registry.paths.cohort_manifests_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{manifest['cohort_manifest_id']}.json"
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"cohort_manifest_id": manifest["cohort_manifest_id"], "path": str(output_path)}, indent=2))


if __name__ == "__main__":
    main()
