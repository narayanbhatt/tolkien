"""Artifact model specialization for stored platform objects."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from tolkien._util.time import utc_now


def required_errors(record: dict[str, Any], required: list[str]) -> list[str]:
    """
    Return validation messages for missing required artifact fields.

    Args:
            record (dict[str, Any]): Row or object dict being validated or flattened.
            required (list[str]): Required field names that must be non-empty.

    Returns:
        List of validation error messages; empty when valid.
    """

    return [f"{field_name} is required" for field_name in required if record.get(field_name) in (None, "")]


@dataclass
class Artifact:
    """Catalogued stored object (file, directory, URI) with provenance metadata."""

    artifact_id: str
    entity_id: str
    artifact_type: str
    artifact_role: str
    version: str = "1"
    status: str = "active"
    path_rel: str = ""
    uri: str = ""
    media_type: str = ""
    format: str = ""
    schema_ref: str = ""
    sha256: str = ""
    byte_size: int | None = None
    created_by_event_id: str = ""
    created_by_run_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source_name: str = "artifact_register"
    source_version: str = "v1"
    ingested_at: str = field(default_factory=utc_now)
    record_version: int = 1
    is_active: bool = True

    def validate(self) -> list[str]:
        """
        Return row-level validation errors for this artifact.
        
        Returns:
        List of validation error messages; empty when valid.
        """

        errors = required_errors(
            asdict(self),
            ["artifact_id", "entity_id", "artifact_type", "artifact_role", "version", "status", "source_name", "source_version"],
        )
        if not self.path_rel and not self.uri:
            errors.append("path_rel or uri is required")
        return errors

    def as_dict(self) -> dict[str, object]:
        """
        Return a storage-neutral dict (``metadata`` not flattened to JSON).
        
        Returns:
        Storage-neutral dict representation of the dataclass.
        """

        return asdict(self)

    @classmethod
    def from_csv_row(self, row: dict[str, str]) -> Artifact:
        """
        Parse one ``artifacts.csv`` row into an :class:`Artifact`.

        Args:
                row (dict[str, str]): Single master-table row dict.

        Returns:
                Parsed :class:`~tolkien.artifacts.models.Artifact` instance.
        """

        md_raw = (row.get("metadata_json") or "").strip()
        metadata: dict[str, Any] = {}
        if md_raw:
            metadata = json.loads(md_raw)
        bs = str(row.get("byte_size") or "").strip()
        byte_size: int | None
        if bs in {"", "None"}:
            byte_size = None
        else:
            byte_size = int(float(bs))
        rv = str(row.get("record_version") or "1").strip()
        record_version = int(float(rv)) if rv else 1
        is_active = str(row.get("is_active", "True")).lower() in ("true", "1", "yes")
        return Artifact(
            artifact_id=row["artifact_id"],
            entity_id=row["entity_id"],
            artifact_type=row["artifact_type"],
            artifact_role=row["artifact_role"],
            version=row.get("version") or "1",
            status=row.get("status") or "active",
            path_rel=row.get("path_rel") or "",
            uri=row.get("uri") or "",
            media_type=row.get("media_type") or "",
            format=row.get("format") or "",
            schema_ref=row.get("schema_ref") or "",
            sha256=row.get("sha256") or "",
            byte_size=byte_size,
            created_by_event_id=row.get("created_by_event_id") or "",
            created_by_run_id=row.get("created_by_run_id") or "",
            metadata=metadata,
            source_name=row.get("source_name") or "artifact_register",
            source_version=row.get("source_version") or "v1",
            ingested_at=row.get("ingested_at") or utc_now(),
            record_version=record_version,
            is_active=is_active,
        )

    def dump(self, registry: object) -> Artifact:
        """
        Append this artifact's registry row via :class:`~tolkien.registry.DatastoreRegistry`.

        Args:
                registry (object): :class:`~tolkien.registry.datastore_registry.DatastoreRegistry` used for catalog writes.

        Returns:
            The persisted :class:`~tolkien.artifacts.models.Artifact` (also written via registry).
        """

        from tolkien.registry.datastore_registry import DatastoreRegistry

        if not isinstance(registry, DatastoreRegistry):
            raise TypeError(f"expected DatastoreRegistry, got {type(registry).__name__}")
        registry.append_artifacts([self])
        return self

    @classmethod
    def load(
        cls,
        registry: object,
        *,
        artifact_id: str | None = None,
        path_rel: str | None = None,
    ) -> Artifact | None:
        """
        Load from master ``artifacts.csv`` via the datastore registry.

        Args:
                registry (object): :class:`~tolkien.registry.datastore_registry.DatastoreRegistry` used for catalog writes.
                artifact_id (str | None): Stable artifact registry identifier. Keyword-only.
                path_rel (str | None): Repository-relative path to a payload or registry row locator. Keyword-only.

        Returns:
                Matching :class:`~tolkien.artifacts.models.Artifact`, or ``None``.
        """

        from tolkien.registry.datastore_registry import DatastoreRegistry

        if not isinstance(registry, DatastoreRegistry):
            raise TypeError(f"expected DatastoreRegistry, got {type(registry).__name__}")
        if artifact_id is not None:
            return registry.load_artifact_by_id(artifact_id)
        if path_rel is not None:
            return registry.load_artifact_by_path_rel(path_rel)
        raise ValueError("provide artifact_id or path_rel")
