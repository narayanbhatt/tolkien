"""Shared CSV read/write."""

from __future__ import annotations

import csv
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    """
    Read a CSV file into a list of row dicts (all values as strings).

    Args:
            path (Path): Filesystem path to read, write, or fingerprint.

    Returns:
            Rows read via ``csv.DictReader`` (all values as strings).
    """

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    """
    Write rows to CSV, creating parent directories as needed.

    Args:
            path (Path): Filesystem path to read, write, or fingerprint.
            rows (list[dict[str, object]]): Table rows represented as string-keyed dicts.
            fieldnames (list[str]): Ordered CSV column headers used for writing.

    Returns:
            None; creates parent directories and writes the CSV file.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
