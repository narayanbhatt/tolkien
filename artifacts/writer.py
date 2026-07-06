"""CSV writer for artifact registry rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from tolkien._util.csv_flatten import flatten_row
from tolkien.artifacts.models import Artifact


ARTIFACT_FIELDS = [
    "artifact_id",
    "entity_id",
    "artifact_type",
    "artifact_role",
    "path_rel",
    "uri",
    "media_type",
    "format",
    "schema_ref",
    "sha256",
    "byte_size",
    "created_by_event_id",
    "created_by_run_id",
    "version",
    "status",
    "metadata_json",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]


class CsvArtifactWriter:
    """Append or overwrite rows in ``artifacts.csv``."""

    def __init__(self, output_path: Path) -> None:
        """
        Target ``artifacts.csv`` (or mirror) for row writes.
        
        Args:
        output_path (Path): Destination CSV path for artifact or primitive writers.
        
        Returns:
        None.
        """
        self.output_path = output_path

    def write(
        self,
        artifacts: Iterable[Artifact],
        append: bool = False,
        *,
        skip_validate: bool = False,
    ) -> int:
        """
        Write artifact rows; return count written.

        Args:
                artifacts (Iterable[Artifact]): Artifact instances to validate and persist.
                append (bool): When ``True``, append rows; when ``False``, overwrite. ``None`` infers from existing file size. Optional.
                skip_validate (bool): When ``True``, skip row validation before writing CSV output. Keyword-only.

        Returns:
                Count of rows written.
        """

        artifact_list = list(artifacts)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append and self.output_path.exists() else "w"
        with self.output_path.open(mode, encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=ARTIFACT_FIELDS)
            if mode == "w":
                writer.writeheader()
            for artifact in artifact_list:
                if not skip_validate:
                    errors = artifact.validate()
                    if errors:
                        raise ValueError(f"{artifact.artifact_id} failed validation: {errors}")
                writer.writerow(flatten_row(artifact.as_dict(), ARTIFACT_FIELDS))
        return len(artifact_list)
