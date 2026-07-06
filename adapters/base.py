"""Shared helpers for local-first modality adapters.

Adapters keep native source files untouched and emit rows for canonical tables.
They should stay small: validate source columns, generate stable IDs, and add
standard lifecycle metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from tolkien._util.csv_io import read_csv, write_csv
from tolkien._util.ids import stable_id


@dataclass
class AdapterResult:
    """Adapter output grouped by target master table name."""

    rows_by_table: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add_rows(self, table_name: str, rows: Iterable[dict[str, object]]) -> None:
        """
        Append rows to a named output table bucket.

        Args:
                table_name (str): Master CSV table stem under validation or adapter output grouping.
                rows (Iterable[dict[str, object]]): Table rows represented as string-keyed dicts.

        Returns:
                None; appends rows to the named table bucket.
        """

        self.rows_by_table.setdefault(table_name, []).extend(rows)


class BaseAdapter:
    """Base contract for source-native to canonical metadata adapters."""

    adapter_name = "base"

    def __init__(self, source_name: str, source_version: str) -> None:
        """
        Stamp ``source_name`` and ``source_version`` on emitted adapter rows.
        
        Args:
            source_name (str): Provenance ``source_name`` stamped on emitted rows.
            source_version (str): Provenance ``source_version`` stamped on emitted rows.

        Returns:
            None.
        """
        self.source_name = source_name
        self.source_version = source_version
        self.ingested_at = datetime.now(timezone.utc).isoformat()

    def lifecycle_fields(self) -> dict[str, object]:
        """
        Standard provenance columns appended to every emitted row.
        
        Returns:
            Standard provenance columns appended to adapter output rows.
        """

        return {
            "source_name": self.source_name,
            "source_version": self.source_version,
            "ingested_at": self.ingested_at,
            "record_version": 1,
            "is_active": True,
        }

    @staticmethod
    def stable_uid(prefix: str, *parts: object) -> str:
        """
        Deterministic ID from stable parts (delegates to :func:`tolkien._util.ids.stable_id`).

        Args:
            prefix (str): Stable identifier prefix segment (for example ``art`` or ``evt``).
            *parts (object): Source values hashed into a deterministic identifier.

        Returns:
                Deterministic identifier built from ``prefix`` and ``parts``.
        """

        return stable_id(prefix, *parts)

    read_csv = staticmethod(read_csv)
    write_csv = staticmethod(write_csv)

    @staticmethod
    def require_columns(rows: list[dict[str, str]], required: set[str], table_name: str) -> None:
        """
        Raise ``ValueError`` when the first row is missing required column names.

        Args:
                rows (list[dict[str, str]]): Table rows represented as string-keyed dicts.
                required (set[str]): Required field names that must be non-empty.
                table_name (str): Master CSV table stem under validation or adapter output grouping.

        Returns:
                None; raises ``ValueError`` when required columns are missing.
        """

        if not rows:
            return
        missing = required.difference(rows[0].keys())
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"{table_name} is missing required columns: {missing_text}")
