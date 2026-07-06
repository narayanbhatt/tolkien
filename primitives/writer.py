"""Writers that flatten storage-neutral primitive records into CSV rows."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from tolkien._util.csv_flatten import flatten_row
from tolkien.primitives.abc import PrimitiveObject


ENTITY_FIELDS = [
    "entity_id",
    "entity_type",
    "name",
    "source_system",
    "source_id",
    "version",
    "status",
    "created_at",
    "metadata_json",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]

EVENT_FIELDS = [
    "event_id",
    "event_type",
    "subject_entity_id",
    "time_anchor",
    "time_offset",
    "time_unit",
    "started_at",
    "ended_at",
    "source_system",
    "source_id",
    "status",
    "metadata_json",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]

OBSERVATION_FIELDS = [
    "observation_id",
    "observation_type",
    "subject_entity_id",
    "event_id",
    "code_system",
    "code",
    "value_type",
    "value_text",
    "value_number",
    "value_boolean",
    "value_unit",
    "method",
    "source_system",
    "source_id",
    "confidence",
    "status",
    "metadata_json",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]

RELATION_FIELDS = [
    "relation_id",
    "relation_type",
    "source_object_type",
    "source_object_id",
    "target_object_type",
    "target_object_id",
    "source_role",
    "target_role",
    "valid_from",
    "valid_to",
    "created_at",
    "source_system",
    "status",
    "metadata_json",
    "source_name",
    "source_version",
    "ingested_at",
    "record_version",
    "is_active",
]

FIELDS_BY_KIND = {
    "entity": ENTITY_FIELDS,
    "event": EVENT_FIELDS,
    "observation": OBSERVATION_FIELDS,
    "relation": RELATION_FIELDS,
}

TABLE_BY_KIND = {
    "entity": "entities",
    "event": "events",
    "observation": "observations",
    "relation": "relations",
}


class CsvPrimitiveWriter:
    """Write primitive objects to canonical CSV mirrors."""

    def __init__(self, output_root: Path) -> None:
        """
        Write primitive CSV mirrors under ``output_root`` (typically ``data/master/csv``).

        Args:
                output_root (Path): Directory root for CSV mirror writes (typically ``data/master/csv``).

        Returns:
                None.
        """

        self.output_root = output_root

    def write(
        self,
        objects: Iterable[PrimitiveObject],
        append: bool = False,
        *,
        skip_validate: bool = False,
    ) -> dict[str, int]:
        """
        Validate (unless skipped), group by kind, and write or append CSV rows.

        Args:
                objects (Iterable[PrimitiveObject]): Primitive objects to validate and persist.
                append (bool): When ``True``, append rows; when ``False``, overwrite. ``None`` infers from existing file size. Optional.
                skip_validate (bool): When ``True``, skip row validation before writing CSV output. Keyword-only.

        Returns:
                Count of rows written.
        """

        grouped: dict[str, list[PrimitiveObject]] = {}
        for obj in objects:
            grouped.setdefault(obj.object_kind, []).append(obj)

        counts: dict[str, int] = {}
        self.output_root.mkdir(parents=True, exist_ok=True)
        for object_kind, object_group in grouped.items():
            fieldnames = FIELDS_BY_KIND[object_kind]
            table_name = TABLE_BY_KIND[object_kind]
            path = self.output_root / f"{table_name}.csv"
            mode = "a" if append and path.exists() else "w"
            with path.open(mode, encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                if mode == "w":
                    writer.writeheader()
                for obj in object_group:
                    if not skip_validate:
                        errors = obj.validate()
                        if errors:
                            raise ValueError(f"{obj.object_kind}:{obj.object_id()} failed validation: {errors}")
                    writer.writerow(flatten_row(obj.as_dict(), fieldnames))
            counts[table_name] = len(object_group)
        return counts
