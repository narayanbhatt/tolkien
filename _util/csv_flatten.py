"""CSV row flattening helpers."""

from __future__ import annotations

import json
from typing import Any


def flatten_metadata_field(record: dict[str, object], fieldnames: list[str]) -> dict[str, object]:
    """
    Coerce ``metadata`` dict to ``metadata_json`` when present in fieldnames.

    Args:
            record (dict[str, object]): Row or object dict being validated or flattened.
            fieldnames (list[str]): Ordered CSV column headers used for writing.

    Returns:
            Row dict with ``metadata`` coerced to ``metadata_json`` when applicable.
    """

    flattened = dict(record)
    metadata = flattened.pop("metadata", None)
    if "metadata_json" in fieldnames:
        if metadata in (None, ""):
            flattened["metadata_json"] = flattened.get("metadata_json", "")
        else:
            flattened["metadata_json"] = json.dumps(metadata, sort_keys=True)
    return flattened


def flatten_row(record: dict[str, object], fieldnames: list[str]) -> dict[str, object]:
    """
    Return a CSV row with None coerced to empty strings.

    Args:
            record (dict[str, object]): Row or object dict being validated or flattened.
            fieldnames (list[str]): Ordered CSV column headers used for writing.

    Returns:
            CSV-ready row dict with ``None`` coerced to empty strings.
    """

    flattened = flatten_metadata_field(record, fieldnames)
    return {field: "" if flattened.get(field, "") is None else flattened.get(field, "") for field in fieldnames}
